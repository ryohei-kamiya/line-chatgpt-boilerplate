FROM public.ecr.aws/lambda/python:3.10-arm64

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install --use-pep517 -r requirements.txt -t .
COPY . ./

# Command can be overwritten by providing a different command in the template directly.
CMD ["app.lambda_handler"]
