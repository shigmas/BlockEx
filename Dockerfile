FROM python:3.5-stretch

ARG SOURCE_COMMIT
ARG SOURCE_BRANCH

WORKDIR /home/root

COPY . /home/root
#RUN sudo apt-get update && sudo apt-get install python3-pip
RUN pip3 install -r requirements.txt

CMD ["tox"]