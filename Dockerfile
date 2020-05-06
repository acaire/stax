FROM python:3.8-alpine
RUN apk add git --update
ARG VERSION
VOLUME /stacks
WORKDIR /stacks
RUN pip install stax==$VERSION
ENTRYPOINT ["stax"]
