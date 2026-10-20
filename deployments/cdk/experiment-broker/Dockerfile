from python:latest
COPY ./build .
# RUN pip install .
# RUN pip install -r activities/requirements.txt
RUN pip install --upgrade pip
RUN pip install ./*.whl
RUN mkdir ~/.aws
CMD ["python", "handler.py"]