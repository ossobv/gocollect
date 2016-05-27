# Note that if you change prefix, you'll have to adjust the files copied
# in install-rc too.
prefix = /usr

SOURCES = $(wildcard *.go) $(wildcard gocollector/*.go)
COLLECTORS = $(wildcard collectors/[a-z]*.*)
# Debian version spec says:
# - tilde sorts before anything, so ~rc1 sorts before final
# - plus and dots are allowed everywhere
VERSION_FROM_DEB := sed -e '1!d;s/.*(\([^)]*\)).*/v\1debuild/' debian/changelog 2>/dev/null
VERSION_FROM_GIT := git describe --tags --match "v[0-9]*" --abbrev=4 HEAD | \
	sed -e 's/_/~/;s/-/+/;s/-/./'  # v0.4_rc1-3-g1234 => v0.4~rc1+3.g1234
VERSION = $(shell $(VERSION_FROM_DEB) || $(VERSION_FROM_GIT))
GOLDFLAGS = -ldflags "-X main.versionStr=$(VERSION)"


.PHONY: all clean
all: gocollect

clean:
	$(RM) gocollect

gocollect: $(SOURCES)
	go build $(GOLDFLAGS) gocollect.go
	# Test version in gocollect -V output; if it's not there, the
	# build it broken for all intents and purposes.
	VERSION_FROM_BIN=`./gocollect -V | sed -e '1!d;s/.* //'`; \
		if test "$$VERSION_FROM_BIN" != "$(VERSION)"; then \
		echo "gocollect -V output fail: $$VERSION_FROM_BIN is not $(VERSION)" >&2 \
		$(RM) gocollect; false; else echo "Built version $(VERSION)"; fi

.PHONY: install install-gocollect install-collectors install-rc
install: install-gocollect install-collectors install-rc
install-gocollect: gocollect
	@echo "Preparing to install binaries: $*"
	install -D gocollect $(DESTDIR)$(prefix)/sbin/gocollect
install-collectors: $(COLLECTORS)
	@echo "Preparing to install collectors: $^"
	install -d $(DESTDIR)$(prefix)/share/gocollect/collectors
	install -t $(DESTDIR)$(prefix)/share/gocollect/collectors $^
install-rc:
	install -D -m0644 gocollect.conf.sample $(DESTDIR)/etc/gocollect.conf.sample
	# The debian postinst scripts use invoke-rc.d to start/stop. On systemd
	# machines that means that we need the SysV init scripts as well.
	if ! initctl --version >/dev/null 2>&1; then \
		install -D -m0755 rc/debian.sysv $(DESTDIR)/etc/init.d/gocollect; \
		install -D -m0644 rc/systemd.service $(DESTDIR)/lib/systemd/system/gocollect.service; \
		systemctl daemon-reload >/dev/null 2>&1 || true; \
	fi
	# The debian postinst scripts would invoke the SysV scripts as well as
	# install the upstart script. Not nice. We need only one.
	if initctl --version >/dev/null 2>&1; then \
		install -D -m0644 rc/upstart.conf $(DESTDIR)/etc/init/gocollect.conf; \
	fi


.PHONY: uninstall uninstall-gocollect uninstall-collectors
uninstall: uninstall-gocollect uninstall-collectors uninstall-rc
uninstall-gocollect:
	$(RM) $(DESTDIR)$(prefix)/sbin/gocollect
uninstall-collectors:
	$(RM) $(addprefix $(DESTDIR)$(prefix)/share/gocollect/,$(COLLECTORS))
	test -d "$(DESTDIR)$(prefix)/sbin" && \
		rmdir -p $(DESTDIR)$(prefix)/sbin; true
	test -d "$(DESTDIR)$(prefix)/share/gocollect" && \
		rmdir -p "$(DESTDIR)$(prefix)/share/gocollect/collectors"; true
uninstall-rc:
	$(RM) $(DESTDIR)/etc/gocollect.conf.sample
	$(RM) $(DESTDIR)/etc/init.d/gocollect
	$(RM) $(DESTDIR)/lib/systemd/system/gocollect.service
	$(RM) $(DESTDIR)/etc/init/gocollect.conf

.PHONY: debian-depends
debian-depends:
	@# E: gocollect: needlessly-depends-on-awk depends
	@# E: gocollect: depends-on-essential-package-without-using-version depends: bash
	@# E: gocollect: depends-on-essential-package-without-using-version depends: coreutils
	@# E: gocollect: depends-on-essential-package-without-using-version depends: debianutils
	@# E: gocollect: depends-on-essential-package-without-using-version depends: dpkg
	@# E: gocollect: depends-on-essential-package-without-using-version depends: findutils
	@# E: gocollect: depends-on-essential-package-without-using-version depends: hostname
	@# E: gocollect: depends-on-essential-package-without-using-version depends: sed
	@# E: gocollect: depends-on-essential-package-without-using-version depends: util-linux
	# NOTE: iproute2 is called iproute on older systems
	# NOTE: kmod is called module-init-tools on older systems
	@sed -e '/^# REQUIRES:/!d;s/^[^:]*: //;s/(.*//' \
		`grep -LE '(LABELS.*optional|LABELS.*hardware-only)' $(COLLECTORS)` \
		| grep -vE '^(awk|bash|coreutils|debianutils|dpkg|findutils|hostname|sed|util-linux)$$' \
		| sort -u | tr '\n' ',' | sed -e 's/,$$//;s/,/, /g'; echo ' (main)'
	@sed -e '/^# REQUIRES:/!d;s/^[^:]*: //;s/(.*//' \
		`grep -lE 'LABELS.*hardware-only' $(COLLECTORS)` \
		| grep -vE '^(awk|bash|coreutils|debianutils|dpkg|findutils|hostname|sed|util-linux)$$' \
		| sort -u | tr '\n' ',' | sed -e 's/,$$//;s/,/, /g'; echo ' (hardware-only)'


TGZ_CONFIG_MD5 = $(shell test -n "$$TGZ_CONFIG" && md5sum /etc/gocollect.conf | sed -e 's/\(.......\).*/\1/')
TGZ_VERSION = $(VERSION)$(shell test -n "$(TGZ_CONFIG_MD5)" && echo "-md5conf-$(TGZ_CONFIG_MD5)")

# TGZ_CONFIG=/etc/gocollect.conf make tgz ==> "gocollect-v0.4~dev-8-g3494-md5conf-c0f48c3.tar.gz"
# wget -qO- http://.../gocollect-v0.4~dev-8-g3494-md5conf-c0f48c3.tar.gz | tar -xzvC /
# if ! which timeout; then printf '#!/bin/sh\nshift; exec "$@"\n' > /usr/bin/timeout; chmod 755 /usr/bin/timeout; fi
# /etc/init.d/gocollect start
.PHONY: tgz
tgz: gocollect-$(TGZ_VERSION).tar.gz

gocollect-$(TGZ_VERSION).tar.gz: gocollect
	# Supply TGZ_CONFIG=/path/to/gocollect.conf in env to copy that
	# config into the tarball.
	$(RM) -r tmp-gocollect-tgz
	mkdir -p tmp-gocollect-tgz
	$(MAKE) DESTDIR=$(CURDIR)/tmp-gocollect-tgz install-gocollect install-collectors
	install -D gocollect-fallback $(CURDIR)/tmp-gocollect-tgz/usr/sbin/gocollect-fallback
	sed -i -e 's/^version=[[:blank:]].*/version="$(VERSION)"/' $(CURDIR)/tmp-gocollect-tgz/usr/sbin/gocollect-fallback
	install -D -m0644 gocollect.conf.sample $(CURDIR)/tmp-gocollect-tgz/etc/gocollect.conf.sample
	if test -n "$$TGZ_CONFIG"; then install -D -m0644 "$$TGZ_CONFIG" $(CURDIR)/tmp-gocollect-tgz/etc/gocollect.conf; fi
	install -D -m0755 rc/generic.sysv $(CURDIR)/tmp-gocollect-tgz/etc/init.d/gocollect
	for n in 0 1 6; do mkdir -p $(CURDIR)/tmp-gocollect-tgz/etc/rc$$n.d; \
		ln -s ../init.d/gocollect $(CURDIR)/tmp-gocollect-tgz/etc/rc$$n.d/K99gocollect; done
	for n in 2 3 4 5; do mkdir -p $(CURDIR)/tmp-gocollect-tgz/etc/rc$$n.d; \
		ln -s ../init.d/gocollect $(CURDIR)/tmp-gocollect-tgz/etc/rc$$n.d/S99gocollect; done
	if ! tar --owner=root --group=root -C tmp-gocollect-tgz -czf gocollect-$(TGZ_VERSION).tar.gz .; then \
		$(RM) gocollect-$(TGZ_VERSION).tar.gz; false; fi
	$(RM) -r tmp-gocollect-tgz
	@echo
	@echo "Created: gocollect-$(TGZ_VERSION).tar.gz"


.PHONY: testrun
testrun: gocollect
	#GOTRACEBACK=system strace -tt -fbexecve ./gocollect -c gocollect-test.conf
	sudo env GOPATH=$$GOPATH GOTRACEBACK=system ./gocollect -c gocollect-test.conf

# .PHONY: fetch-new-package
# fetch-new-package:
# 	# Be sure to set GOPATH; see ./gorc.
# 	go get github.com/XXX
