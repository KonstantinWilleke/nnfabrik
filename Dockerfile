FROM sinzlab/pytorch:v3.8-torch1.7.0-cuda11.0-dj0.12.7

ADD . /src/nnfabrik
WORKDIR /src

RUN pip3 install -e /src/nnfabrik
RUN pip3 install -e /src/nnfabrik/ml-utils
RUN pip3 install -e /src/nnfabrik/nnvision/nnvision
RUN pip3 install -e /src/nnfabrik/dataport/data_port
RUN pip3 install -e /src/nnfabrik/nndichromacy/nndichromacy
RUN pip3 install -e /src/nnfabrik/mei/mei
RUN pip3 install -e /src/nnfabrik/insilico_stimuli/insilico-stimuli
RUN pip3 install -e /src/nnfabrik/fitgabor
RUN pip3 install -e /src/nnfabrik/nnidentify
RUN pip3 install git+https://github.com/sacadena/ptrnets
RUN pip3 install git+https://github.com/dicarlolab/CORnet
RUN pip3 install --upgrade --force-reinstall torch==1.7.0 torchvision==0.8.1 -f https://download.pytorch.org/whl/cu102/torch_stable.html
WORKDIR /notebooks