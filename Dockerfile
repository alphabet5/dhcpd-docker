FROM python:3.9-alpine as builder


RUN apk add --no-cache openssl-dev libffi-dev libressl-dev musl-dev libffi-dev gcc python3-dev
RUN mkdir /whl
RUN python3.9 -m pip wheel --wheel-dir=/whl jinja2 rich ciscoconfparse napalm pyyaml


FROM python:3.9-alpine
LABEL maintainer="alphabet5"

ENV SW_USER=username
ENV SW_PASS=password

RUN \
 echo "**** install packages ****" && \
 apk add --no-cache dhcp bash && \
 mkdir /whl

COPY --from=builder /whl/* /whl/
COPY entrypoint.sh /entrypoint.sh
COPY template-generation.py /template-generation.py
COPY helper.py /helper.py

RUN chmod 755 /entrypoint.sh
RUN touch /var/lib/dhcp/dhcpd.leases
RUN python3.9 -m pip install --no-cache-dir --upgrade pip
RUN python3.9 -m pip install --no-cache-dir /whl/*

EXPOSE 53/tcp 53/udp

ENTRYPOINT ["/entrypoint.sh"]