# Note that if you change prefix, you'll have to adjust the files copied
# in install-rc too.
prefix = /usr

SOURCES = $(wildcard *.go) $(wildcard gocollector/*.go)
COLLECTORS = $(wildcard collectors/[a-z]*.*)
VERSION = $(shell git describe --tags --match "v[0-9]*" --abbrev=4 HEAD | tr '_' '~')
GOLDFLAGS = -ldflags "-X main.versionStr=$(VERSION)"


.PHONY: all clean
all: gocollect

clean:
	$(RM) gocollect

gocollect: $(SOURCES)
	go build $(GOLDFLAGS) gocollect.go

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
	@# E: gocollect: depends-on-essential-package-without-using-version depends: coreutils
	@# E: gocollect: depends-on-essential-package-without-using-version depends: debianutils
	@# E: gocollect: depends-on-essential-package-without-using-version depends: dpkg
	@# E: gocollect: depends-on-essential-package-without-using-version depends: findutils
	@# E: gocollect: depends-on-essential-package-without-using-version depends: hostname
	@# E: gocollect: depends-on-essential-package-without-using-version depends: sed
	@# E: gocollect: depends-on-essential-package-without-using-version depends: util-linux
	@# E: gocollect: needlessly-depends-on-awk depends
	@sed -e '/^# REQUIRES:/!d;s/^[^:]*: //;s/(.*//' $(COLLECTORS) \
		| grep -vE '^(awk|coreutils|debianutils|dpkg|findutils|hostname|sed|util-linux)$$' \
		| sort -u | tr '\n' ',' | sed -e 's/,$$//;s/,/, /g'; echo


.PHONY: testrun
testrun: gocollect
	#GOTRACEBACK=system strace -tt -fbexecve ./gocollect -c gocollect-test.conf
	sudo env GOPATH=$$GOPATH GOTRACEBACK=system ./gocollect -c gocollect-test.conf

# .PHONY: fetch-new-package
# fetch-new-package:
# 	# Be sure to set GOPATH; see ./gorc.
# 	go get github.com/XXX
