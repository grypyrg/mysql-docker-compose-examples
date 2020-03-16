FROM python:3

RUN pip install protobuf dnspython
RUN apt-get update
RUN apt-get install -y dnsutils

ADD connector-python-wl13372-export-with-doc /connector-python-wl13372-export-with-doc

RUN cd /connector-python-wl13372-export-with-doc && python setup.py install

ADD resolv.conf /etc/resolv.conf
ADD test-dns-srv.py /

WORKDIR "/"

CMD [ "python", "test-dns-srv.py", "--version" ]
#CMD [ "python", "--version" ]
