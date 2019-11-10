FROM jcarrano/sphinx-doc AS build-env

ADD . /src
RUN cd /src && python3 setup.py sdist

FROM jcarrano/sphinx-doc
COPY --from=build-env /src/dist/antidox-*.tar.gz /tmp/
RUN apk add --no-cache py3-lxml doxygen && \
    pip3 --no-cache-dir install /tmp/antidox-*.tar.gz
