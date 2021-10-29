from collections import OrderedDict
import itertools
import json
import logging
import pika
from os import environ
from urllib.parse import urljoin, urlparse
import sys

from netaddr import IPNetwork
from requests import Session

from lib.envparse import rmq_uri
from lib.rmq.rmq_consumer import RMQConsumer

logging.getLogger('pika').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
log = logging.getLogger(__name__)

IPV6_LOOPBACK = IPNetwork('::1/128')

ALL_KEYS = 'all'
CORE_ID = 'core.id'
OS_NETWORK = 'os.network'
SYS_IPMI = 'sys.ipmi'


class Http404Error(Exception):
    pass


class MultipleResourcesError(Exception):
    pass


class RequestError(Exception):
    pass


class NetboxRequest:
    def __init__(self, url):
        self.session = Session()
        if url.password:
            self.session.headers.update({
                'Authorization': f'Token {url.password}',
            })
        # Drop the username/password.
        self.url = url._replace(netloc=url.netloc.split('@')[-1]).geturl()

    def request(self, method, url, **kwargs):
        if not url.startswith('https://'):
            url = urljoin(self.url, url)
        response = self.session.request(method, url, **kwargs)
        log.debug(
            'method=%s, url=%s, kwargs=%r, response=%r',
            method, url, kwargs, response)
        return response

    def get(self, url, **kwargs):
        response = self.request('GET', url, **kwargs)
        if response.status_code != 200:
            raise RequestError(url, kwargs, response.text)
        return response.json()

    def post(self, url, **kwargs):
        response = self.request('POST', url, **kwargs)
        if response.status_code != 201:
            raise RequestError(url, kwargs, response.text)
        return response.json()

    def patch(self, url, **kwargs):
        response = self.request('PATCH', url, **kwargs)
        if response.status_code != 200:
            raise RequestError(url, kwargs, response.text)
        return response.json()

    def delete(self, url, **kwargs):
        response = self.request('DELETE', url, **kwargs)
        if response.status_code == 404:
            raise Http404Error(url, kwargs, response.text)
        elif response.status_code != 204:
            raise RequestError(url, kwargs, response.text)
        return response

    def get_list(self, url, params=None):
        if params is not None and params.get('limit') is not None:
            return self.get(url, params=params)

        results = []
        while url is not None:
            data = self.get(url, params=params)
            url, params = data['next'], None
            results.extend(data['results'])
        return {
            'count': data['count'],
            'previous': None,
            'next': None,
            'results': results,
        }

    def get_prefix_for_ip(self, ip):
        url, params = '/api/ipam/prefixes/', {'contains': str(ip)}
        while True:
            prefixes = self.get(url, params=params)
            if prefixes['next'] is not None:
                url, params = prefixes['next'], None
                continue
            if prefixes['count'] > 0:
                # The last entry is the closest prefix.
                return prefixes['results'][-1]
            return None

    def get_addresses(self, address, limit=None):
        params = {
            'address':  str(address),
            'limit': limit,
        }
        return self.get_list('/api/ipam/ip-addresses/', params=params)

    def get_by_params(self, url, params, klass=None):
        data = self.get(url, params=params)
        if data['count'] == 1:
            if klass:
                return klass(data['results'][0], self)
            return data['results'][0]
        elif data['count'] > 1:
            raise MultipleResourcesError(
                f'Found {data["count"]} results on {url} with {params}')
        return None

    def get_by_regid(self, klass, regid):
        return self.get_by_params(klass.url, {'cf_gocollect_id': regid}, klass)

    def get_by_fqdn(self, klass, fqdn):
        # Do a search on the fqdn in variations to catch differences in name.
        search_params = set([
            fqdn,  # host-with-dash-in-name
            fqdn.replace('-', '.'),  # host.with.dash.in.name
        ])
        for q in search_params:
            obj = self.get_by_params(
                klass.url, {'q': q, 'status': ('active', 'planned', 'staged')},
                klass)
            if (obj is not None
                    and obj.obj['custom_fields']['gocollect_id'] is None):
                return obj


class BaseResource:
    url = None
    param = None
    role_attr = None
    interface_url = None
    interface_type = None
    interface_param = None
    iface_type = 'virtual'
    bmc_interface = 'BMC'
    special_interfaces = (bmc_interface,)

    def __str__(self):
        return self.obj["display"]

    @classmethod
    def set_defaults(cls, **kwargs):
        cls.roles_skip_interfaces = kwargs.get('roles_skip_interfaces', ())

    def __init__(self, obj, netbox):
        self.obj = obj
        self.netbox = netbox

    @classmethod
    def create(cls, data, netbox):
        data = cls.get_create_data(data, netbox)
        return cls(netbox.post(cls.url, json=data), netbox)

    @classmethod
    def get_create_data(cls, data, netbox):
        raise NotImplementedError()

    def update(self, data, dry_run=False):
        updates = self.get_update_data(data)
        if updates:
            if dry_run:
                log.info('Would update %s using %r', self, updates)
            else:
                log.info('%s applying update %r', self, updates)
                return self.__class__(
                    self.netbox.patch(self.obj['url'], json=updates),
                    self.netbox)
        return self

    def get_update_data(self, data):
        updates, custom_fields = {}, {}
        if data['fqdn'] != self.obj['name']:
            updates['name'] = data['fqdn']
        # Set primary ip if available on any interface and only when not
        # currently set.
        if self.obj['primary_ip4'] is None and data.get('ip4'):
            addresses = self.get_addresses(address=data['ip4'], limit=2)
            if addresses['count'] == 1:
                updates['primary_ip4'] = addresses['results'][0]['id']
        if self.obj['primary_ip6'] is None and data.get('ip6'):
            addresses = self.get_addresses(address=data['ip6'], limit=2)
            if addresses['count'] == 1:
                updates['primary_ip6'] = addresses['results'][0]['id']
        if data.get('machine-id') != self.obj['custom_fields']['machine_id']:
            custom_fields['machine_id'] = data.get('machine-id')
        # Set the gocollect id only when not currently set.
        if self.obj['custom_fields']['gocollect_id'] is None:
            custom_fields['gocollect_id'] = data['regid']

        if custom_fields:
            updates['custom_fields'] = custom_fields
        return updates

    def get_addresses(self, address=None, interface=None, limit=None):
        params = {
            self.param:  self.obj["id"],
            self.interface_param: interface,
            'limit': limit,
        }
        if address is not None:
            params['address'] = str(address)
        return self.netbox.get_list('/api/ipam/ip-addresses/', params=params)

    def get_interface_by_name(self, name):
        params = {
            self.param: self.obj["id"],
            'name': name,
        }
        return self.netbox.get_by_params(self.interface_url, params=params)

    def search_interface_by_name(self, name):
        params = {
            self.param: self.obj["id"],
            'q': name,
        }
        return self.netbox.get_by_params(self.interface_url, params=params)

    def get_interfaces(self, limit=None):
        params = {
            self.param:  self.obj["id"],
            'limit': limit,
        }
        return self.netbox.get_list(self.interface_url, params=params)

    def get_role(self):
        if self.obj[self.role_attr]:
            return self.obj[self.role_attr]['slug']

    def sync_interfaces(self, data, dry_run=False):
        # Skip interface updates for some roles.
        if self.roles_skip_interfaces:
            role = self.get_role()
            if role is not None and role.startswith(
                    self.roles_skip_interfaces):
                log.info('Skipping interfaces for %s with role %s',
                         self.obj['display'], role)
                return

        # List of interfaces with their IP addresses.
        addresses = {
            (i['assigned_object_type'], i['assigned_object_id'],
                i['address']): i
            for i in self.get_addresses()['results']}
        interfaces = {
            i['name']: i
            for i in self.get_interfaces()['results']}
        data = self.prepare_interface_data(data)

        special_interfaces = self.rename_or_remove_not_configured_interfaces(
            data, interfaces, addresses, dry_run)

        # Keep track which interface/IP address combinations are configured
        # on the gocollect node.
        seen_addresses = []
        for name, iface in data.items():
            if name in self.special_interfaces:
                continue
            if not self.is_meaningful_interface(iface):
                continue
            # Parents may not exist in data preparation stage.
            if iface['parent']:
                if iface['parent'] in interfaces:
                    iface['parent'] = interfaces[iface['parent']]['id']
                else:
                    iface['parent'] = None
            interfaces[name] = self.create_or_update_interface(
                iface, interfaces, dry_run)
            interface_id = interfaces[name]['id']
            for ip in iface['ip']:
                if not self.is_meaningful_address(ip):
                    continue
                key = (self.interface_type, interface_id, str(ip))
                seen_addresses.append(key)
                if key not in addresses:
                    # Assign IP addresses which have not been assigned.
                    self.assign_ip_address(interface_id, ip, dry_run)

        # Remove addresses which are not configured on the gocollect node.
        for key, address in addresses.items():
            if (key not in seen_addresses
                    and address['assigned_object_id']
                    not in special_interfaces):
                if dry_run:
                    log.info(
                        'Would remove %s ipaddress %s', self,
                        address['display'])
                else:
                    try:
                        self.netbox.delete(address['url'])
                        log.info(
                            '%s removed ipaddress %s', self,
                            address['display'])
                    except Http404Error:
                        # The interface with the address was removed.
                        pass

    def create_or_update_interface(self, data, interfaces, dry_run):
        # Remove ip from the post data.
        data = {k: v for k, v in data.items() if k not in ('ip',)}
        interface = interfaces.get(data['name'])
        if interface is not None:
            updates = {}
            for param in list(data.keys()):
                if param in (self.param[:-3], 'parent'):
                    # device/vm/parent is a nested object.
                    value = (
                        interface[param]['id'] if interface[param] else None)
                    if data[param] != value:
                        updates[param] = data[param]
                elif param == 'type':
                    # Type is a value/label dictionary.
                    if (param in interface
                            and data[param] != interface[param]['value']):
                        updates[param] = data[param]
                elif param in interface and data[param] != interface[param]:
                    updates[param] = data[param]
            if updates:
                if dry_run:
                    log.info(
                        'Would update %s interface %s with %r', self,
                        interface['display'], updates)
                else:
                    interface = self.netbox.patch(
                        interface['url'], json=updates)
                    log.info(
                        '%s updated interface %s with %r', self,
                        interface['display'], updates)
        elif dry_run:
            log.info(
                'Would create %s interface %s using %r', self, data['name'],
                data)
            data['id'] = 'dry-run-' + data['name']
            return data
        else:
            interface = self.netbox.post(self.interface_url, json=data)
            log.info('%s created interface %s', self, interface['display'])
        return interface

    def rename_or_remove_not_configured_interfaces(
            self, data, interfaces, addresses, dry_run):
        special_interfaces = []
        for name in list(interfaces.keys()):
            if name in self.special_interfaces:
                special_interfaces.append(interfaces[name]['id'])
                continue
            if name in data:
                continue

            iface = interfaces.pop(name)
            new_name = self.find_new_interface_name_with_ip(
                iface, data, addresses)
            if new_name is not None and new_name not in interfaces:
                if dry_run:
                    log.info(
                        'Would rename %s interface %s to %s', self,
                        iface['display'], new_name)
                else:
                    interfaces[new_name] = self.netbox.patch(
                        iface['url'], json={'name': new_name})
                    log.info(
                        '%s renamed interface %s to %s', self,
                        iface['display'], new_name)
            elif iface.get('cable') or iface.get('connected_endpoint'):
                log.warning(
                    'Preserving %s interface %s because it is connected '
                    'with cable %r to endpoint %r', self, iface['display'],
                    iface['cable'], iface['connected_endpoint'])
            elif dry_run:
                log.info(
                    'Would remove %s interface %s', self, iface['display'])
            else:
                self.netbox.delete(iface['url'])
                log.info('%s removed interface %s', self, iface['display'])

        return special_interfaces

    def find_new_interface_name_with_ip(self, iface, data, addresses):
        # If an interface was named differently between host/netbox try to find
        # the interface by matching it's ip addresses.
        candidates, ips = set(), []
        for iface_type, iface_id, iface_ip in addresses:
            if iface_id != iface['id']:
                continue
            for name, iface_data in data.items():
                for ip in iface_data['ip']:
                    if str(ip) == iface_ip:
                        ips.append(iface_ip)
                        candidates.add(name)
        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            raise ValueError(
                'Cannot uniquely identify the interface name matching '
                f'addresses {ips}: {candidates}')

    def prepare_interface_data(self, data):
        interfaces = []
        for name, iface in data['interfaces'].items():
            parent = None
            if '@' in name:
                name, parent = name.split('@')
            if parent:
                iface_type = 'virtual'
            elif name.startswith(('em', 'en', 'eth')):
                iface_type = self.iface_type
            else:
                iface_type = 'virtual'
            interfaces.append({
                'name': name,
                self.param[:-3]: self.obj['id'],
                'mac_address': iface['mac'].upper() or None,
                'parent': parent,
                'type': iface_type,
                'ip': [IPNetwork(f'{i["address"]}/{i["bits"]}')
                       for i in itertools.chain(iface['ip4'], iface['ip6'])],
            })
        return OrderedDict(
            (i['name'], i)
            for i in sorted(
                interfaces, key=lambda i: (
                    i['parent'] is not None, i['parent'], i['name'])))

    def is_meaningful_interface(self, iface):
        if iface['name'].startswith(('em', 'en', 'eth')):
            # Always include hardware interfaces.
            return True
        elif iface['name'].startswith(('br-', 'cali', 'docker', 'fl', 'fw')):
            # Blacklist local interfaces.
            return False
        elif iface['mac_address'] in ('ee:ee:ee:ee:ee:ee', '0.0.0.0'):
            # Bad mac address seen on cali and tunnel interfaces.
            return False
        elif any(self.is_meaningful_address(i) for i in iface['ip']):
            # Virtual interfaces with a meaningful IP address.
            return True
        return False

    def is_meaningful_address(self, ip):
        # https://github.com/netaddr/netaddr/issues/222
        # netaddr with fix is not released.
        if ip in IPV6_LOOPBACK:
            return False
        return not (ip.is_loopback() or ip.is_link_local())

    def assign_ip_address(self, interface_id, ip, dry_run):
        addresses = []
        assigned_addresses = {}
        for address in self.netbox.get_addresses(str(ip))['results']:
            addresses.append(address)
            if address['assigned_object'] is not None:
                assigned_addresses[
                    (address['assigned_object_type'],
                        address['assigned_object_id'])] = address

        if (self.interface_type, interface_id) in assigned_addresses:
            # The address is assigned to the interface.
            return

        is_anycast = bool(len(addresses) > 0 and all(
                bool(i['role'] and i['role']['value'] == 'anycast')
                for i in addresses))
        if len(addresses) > 0 and not assigned_addresses:
            # Address exists but is not assigned.
            address = addresses[0]
            if dry_run:
                log.info(
                    'Would update %s ipaddress %s', self, address['display'])
            else:
                address = self.netbox.patch(address['url'], json={
                    'assigned_object_type': self.interface_type,
                    'assigned_object_id': interface_id,
                })
                log.info('%s updated ipaddress %s', self, address['display'])
        elif len(addresses) > 0 and assigned_addresses and not is_anycast:
            # Address is assigned to another interface.
            log.warning(
                '%s cannot assign %s to %s:%s, used by %s', self, ip,
                self.interface_type, interface_id, assigned_addresses.keys())
        elif len(addresses) == 0 or (
                len(addresses) > 0 and assigned_addresses and is_anycast):
            # Address does not exist or has the anycast role.
            # Determine the context by searching prefixes.
            prefix = self.netbox.get_prefix_for_ip(ip)
            vrf = prefix['vrf']['id'] if prefix and prefix['vrf'] else None
            data = {
                'address': str(ip),
                'assigned_object_type': self.interface_type,
                'assigned_object_id': interface_id,
                'vrf': vrf,
                'role': 'anycast' if is_anycast else None,
            }
            if dry_run:
                log.info(
                    'Would create %s ipaddress %s with %r', self, ip, data)
            else:
                address = self.netbox.post(
                    '/api/ipam/ip-addresses/', json=data)
                log.info('%s created ipaddress %s', self, address['display'])

    def create_or_update_ipmi(self, data, dry_run=False):
        if 'error' in data:
            log.debug('%s does not have IPMI devices', self)
            return
        elif data['IP Address'] == '0.0.0.0':
            log.debug('%s does not have a valid IPMI IP', self)
            return

        ip = IPNetwork(f'{data["IP Address"]}/{data["Subnet Mask"]}')
        interface = self.get_interface_by_name(self.bmc_interface)
        if interface is None:
            # Try with a broader search request.
            for name in (self.bmc_interface, 'IPMI'):
                interface = self.search_interface_by_name(name)
                if interface is not None:
                    break

        if interface is not None:
            updates = {}
            if data['MAC Address'].upper() != interface['mac_address']:
                updates['mac_address'] = data['MAC Address']
            if interface['name'] != self.bmc_interface:
                updates['name'] = self.bmc_interface

            if updates:
                if dry_run:
                    log.info(
                        'Would update %s interface %s with %r', self,
                        interface['display'], updates)
                else:
                    interface = self.netbox.patch(
                        interface['url'], json=updates)
                    log.info(
                        '%s updated interface %s', self, interface['display'])
        elif dry_run:
            log.info('Would create %s interface %s', self, self.bmc_interface)
            return
        else:
            interface = self.netbox.post(self.interface_url, json={
                'name': self.bmc_interface,
                self.param[:-3]: self.obj['id'],
                'mac_address': data['MAC Address'].upper() or None,
                'type': self.iface_type,
                'mgmt_only': True,
            })
            log.info('%s created interface %s', self, interface['display'])

        addresses = self.get_addresses(interface=interface['id'])['results']
        if len(addresses) == 1 and addresses[0]['address'] == str(ip):
            return
        self.assign_ip_address(interface['id'], ip, dry_run)
        for address in addresses:
            if address['address'] != str(ip):
                if dry_run:
                    log.info(
                        'Would remove %s ipaddress %s', self,
                        address['display'])
                else:
                    self.netbox.delete(address['url'])
                    log.info(
                        '%s removed ipaddress %s', self, address['display'])


class Device(BaseResource):
    url = '/api/dcim/devices/'
    param = 'device_id'
    interface_url = '/api/dcim/interfaces/'
    interface_param = 'interface_id'
    interface_type = 'dcim.interface'
    role_attr = 'device_role'

    @classmethod
    def set_defaults(cls, **kwargs):
        cls.iface_type = kwargs.get('iface_type')
        cls.role = kwargs.get('role')
        cls.type = kwargs.get('type')
        cls.site = kwargs.get('site')

    @classmethod
    def get_create_data(cls, data, netbox):
        if 'ip4' in data:
            prefix = netbox.get_prefix_for_ip(data['ip4'])
        elif 'ip6' in data:
            prefix = netbox.get_prefix_for_ip(data['ip6'])
        else:
            prefix = None
        site = prefix['site']['id'] if prefix and prefix['site'] else cls.site
        return {
            'name': data['fqdn'],
            'device_role': cls.role,
            'device_type': cls.type,
            'site': site,
            'custom_fields': {
                'service_code_device': 'netbox-device',
                'gocollect_id': data['regid'],
                'machine_id': data.get('machine-id'),
            }
        }


class VM(BaseResource):
    url = '/api/virtualization/virtual-machines/'
    param = 'virtual_machine_id'
    interface_url = '/api/virtualization/interfaces/'
    interface_param = 'vminterface_id'
    interface_type = 'virtualization.vminterface'
    role_attr = 'role'

    @classmethod
    def set_defaults(cls, **kwargs):
        cls.cluster = kwargs.get('cluster')

    @classmethod
    def get_create_data(cls, data, netbox):
        return {
            'name': data['fqdn'],
            'cluster': cls.cluster,
            'custom_fields': {
                'gocollect_id': data['regid'],
                'machine_id': data.get('machine-id'),
            }
        }


class Storage(object):
    keys = [
        CORE_ID,
        OS_NETWORK,
        SYS_IPMI,
    ]

    def __init__(self, netbox, dry_run):
        self.netbox = netbox
        if ALL_KEYS in dry_run:
            self.dry_run = self.keys[:]
        else:
            self.dry_run = dry_run

    def create_resource(self, data):
        if ('system-manufacturer' not in data
                or data['system-manufacturer'] in ('QEMU', 'Xen')):
            Resource = VM
        else:
            Resource = Device
        # The resource may exist without the gocollect id.
        obj = self.netbox.get_by_fqdn(Resource, data['fqdn'])
        if obj is not None:
            if CORE_ID in self.dry_run:
                log.info(
                    'Would associate %s with %s using %r', data['regid'],
                    obj, obj.get_update_data(data))
            else:
                log.info(
                    'Associated %s with %s %s', data['regid'], obj,
                    obj.obj['url'])
                return obj.update(data)
        elif CORE_ID in self.dry_run:
            log.info(
                'Would create %s for %s using %r', data['regid'], data['fqdn'],
                Resource.get_create_data(data, self.netbox))
        else:
            obj = Resource.create(data, self.netbox)
            log.info(
                'Created %s for %s %s', data['regid'], obj, obj.obj['url'])
            return obj

    def get_resource(self, regid):
        for Resource in (Device, VM):
            obj = self.netbox.get_by_regid(Resource, regid)
            if obj is not None:
                return obj

    def store(self, regid, collectkey, data):
        obj = self.get_resource(regid)
        if obj is None and collectkey == CORE_ID:
            # Need core.id to create the object.
            self.create_resource(data)
        elif obj is not None:
            log.info(
                'Updating %s:%s on %s %s', regid, collectkey, obj,
                obj.obj['url'])
            if collectkey == CORE_ID:
                obj.update(data, dry_run=bool(CORE_ID in self.dry_run))
            elif collectkey == OS_NETWORK:
                obj.sync_interfaces(
                    data, dry_run=bool(OS_NETWORK in self.dry_run))
            elif collectkey == SYS_IPMI:
                obj.create_or_update_ipmi(
                    data, dry_run=bool(SYS_IPMI in self.dry_run))

    def callback(self, ch, method, properties, body):
        try:
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            json_body = json.loads(body)

            regid = json_body.get('regid')
            if regid is None:
                log.error('No regid found!!! %s', body)
                return

            collectkey = json_body.get('collectkey')
            if collectkey not in self.keys:
                log.debug('Nothing to do for collectkey %s', collectkey)
                return

            ip = json_body.get('seenip'),
            log.info('Updating %s:%s from %s', regid, collectkey, ip)
            self.store(regid, collectkey, json_body.get('data', {}))
        except Exception:  # Never crash
            log.exception('Error processing message body: %r', body)


def main():
    logging.basicConfig(level=environ.get('RMQ2NB_LOGLEVEL', 'INFO').upper())
    # rmq://HOST[:PORT]/VIRTUAL_HOST/EXCHANGE[/QUEUE]
    rmq_url = rmq_uri(environ.get('RMQ2NB_RMQ_URI', ''))
    netbox_url = urlparse(environ.get('RMQ2NB_NB_URI'))
    dry_run = tuple(environ.get('RMQ2NB_DRY_RUN', ALL_KEYS).split())
    device_iface_type = environ.get(
        'RMQ2NB_NB_DEVICE_IFACE_TYPE', '1000base-t')
    device_role = int(environ.get('RMQ2NB_NB_DEVICE_ROLE_ID', 1))
    device_type = int(environ.get('RMQ2NB_NB_DEVICE_TYPE_ID', 1))
    roles_skip_interfaces = tuple(environ.get(
        'RMQ2NB_NB_ROLES_SKIP_INTERFACES', '').split())
    site = int(environ.get('RMQ2NB_NB_SITE_ID', 1))
    vm_cluster = int(environ.get('RMQ2NB_NB_VM_CLUSTER_ID', 1))
    BaseResource.set_defaults(roles_skip_interfaces=roles_skip_interfaces)
    Device.set_defaults(
        iface_type=device_iface_type, role=device_role, type=device_type,
        site=site)
    VM.set_defaults(cluster=vm_cluster)

    netbox = NetboxRequest(netbox_url)
    storage = Storage(netbox, dry_run=dry_run)

    if 'test' in sys.argv:
        storage.callback(None, None, None, sys.stdin.read())
        sys.exit()

    credentials = pika.credentials.PlainCredentials(
        rmq_url.username, rmq_url.password)

    parameters = pika.ConnectionParameters(
        host=rmq_url.host, heartbeat_interval=10, virtual_host=rmq_url.vhost,
        credentials=credentials)

    consumer = RMQConsumer(
        parameters, storage.callback, rmq_url.exchange, rmq_url.routing_key,
        rmq_url.queue)

    try:
        log.info('Starting with dry_run=%r', dry_run)
        consumer.run()
    except (KeyboardInterrupt, SystemExit):
        consumer.stop()
        log.info('Exited')
