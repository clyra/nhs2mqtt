# nhs2mqtt

Esse é um script simples que lê os dados enviados pelos nobreaks NHS com interface USB e os publica em um broker MQTT. Instale os pacotes de pré-requisitos com um "pip3 install -r requirements", copie/edite o arquivo de configuração e execute o script com:

```
python3 nhs2mqtt.py config.yaml  
```

É possível usar o script sem um servidor mqtt bastando remover toda a seção "mqtt" da configuração (será necessário habilitar o debug para ver os valores no console.

## Utilizando no Home Assistant

O objetivo desse script é o de verificar estado da energia elétrica em casa, baseando-se nas informações do nobreak. O exemplo abaixo cria um sensor para isso:

```
binary_sensor:
  - platform: mqtt
    name: ups
    state_topic: "home/UPS/state"
    device_class: power
    availability_topic: "home/UPS/LWT"
    payload_available: "Online"
    payload_not_available: "Offline"
    json_attributes_topic: "home/UPS/attributes"


