FROM sinzlab/pytorch:v3.8-torch1.5.0-cuda10.2-dj0.12.4

ADD . /src/nnfabrik
WORKDIR /src

RUN pip3 install -e nnfabrik
RUN pip3 install -e nnfabrik/ml-utils
RUN pip3 install -e nnfabrik/nnvision/nnvision
RUN pip3 install -e nnfabrik/dataport/data_port
RUN pip3 install -e nnfabrik/nndichromacy/nndichromacy
RUN pip3 install -e nnfabrik/mei/mei

WORKDIR /notebooks