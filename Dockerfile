FROM python:3.8-alpine
RUN apk --no-cache add git
ARG VERSION
VOLUME /stacks
WORKDIR /stacks
RUN pip install stax==$VERSION
ENTRYPOINT ["stax"]
