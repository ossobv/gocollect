.PHONY: all clean gocollect-client

all: gocollect-client

gocollect-client:
	$(MAKE) -C gocollect-client

clean:
	$(MAKE) -C gocollect-client clean
