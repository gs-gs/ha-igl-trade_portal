FROM python:3.8

WORKDIR /usr/src/app
COPY ./ /usr/src/app

RUN pip install -r requirements.txt

# Support AWS KMS encryption
RUN pip install awscli
ENTRYPOINT [ "bash", "/usr/src/app/entrypoint.sh" ]

CMD [ "python", "./issue.py" ]
