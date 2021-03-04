FROM sinzlab/pytorch:v3.8-torch1.7.0-cuda11.0-dj0.12.7

ADD . /src/nnfabrik
WORKDIR /src

RUN pip3 install -e nnfabrik
RUN pip3 install -e nnfabrik/ml-utils
RUN pip3 install -e nnfabrik/nnvision/nnvision
RUN pip3 install -e nnfabrik/dataport/data_port
RUN pip3 install -e nnfabrik/nndichromacy/nndichromacy
RUN pip3 install -e nnfabrik/mei/mei
RUN pip3 install git+https://github.com/sacadena/ptrnets
RUN pip3 install git+https://github.com/dicarlolab/CORnet

WORKDIR /notebooks