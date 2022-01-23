import asyncio
import json
import serial
import struct
import sys
import paho.mqtt.client as mqtt #import the client1
import yaml


s = serial.Serial('/dev/ttyACM0')
state = 'UNKNOW'

class MyMQTT:

    def __init__(self, host, port, topic, user="", password=""):

        self.host = host
        self.port = port
        self.base_topic = topic
        self.state_topic = self.base_topic + '/state'
        self.attr_topic = self.base_topic + '/attributes'
        self.lwt_topic = self.base_topic + '/LWT'
        self.user = user
        self.password = password

        self.client = mqtt.Client("nhs2mqtt")

        if self.user and self.password:
            self.client.username_pw_set(self.user, self.password)

        try:
            self.client.connect(self.host, self.port)
            self.client.publish(self.lwt_topic, payload="Online", retain=True)
            self.client.will_set(self.lwt_topic, payload="Offline", retain=True)
        except Exception as e:
            print(e)
            sys.exit()

        self.inicia_loop()

    def atualiza_status(self, status):

        self.client.publish(self.state_topic, payload=status)

    def atualiza_atributos(self, attr):

        self.client.publish(self.attr_topic, payload=attr)

    def inicia_loop(self):

        self.client.loop_start()

    def para_loop(self):

       self.client.publish(self.lwt_topic, payload="Offline", retain=True)
       self.client.loop_stop()

class NHS:

    def __init__(self, porta_serial, mqtt_client, rate=20, debug=False):

        self.porta_serial = porta_serial
        self.mqtt_client = mqtt_client
        self.state = 'UNKNOW'
        self.rate = rate
        self.debug = debug

        self.counter = 0

        try:
            self.serial = serial.Serial(self.porta_serial)
        except Exception as e:
            print(e)
            sys.exit()

    def run_forever(self):
        loop = asyncio.get_event_loop()
        loop.add_reader(self.serial, self.read_serial)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
            if self.mqtt_client:
                mqtt_client.para_loop()


    def read_serial(self):
        '''
        read a line
        '''
        line = []
        msg = s.read()
        while (msg != b'\xff'):
            line.append(msg)
            msg = s.read()
        self.counter +=1
        if len(line) == 20:
            # hopefully a dataframe
            self.process_frame(line)
        else:
            #print(len(line))
            return
        #if state != newstate:
        #    state = newstate
        #    print(state, newstate)
        #    client.publish("home/UPS", state)

    def process_frame(self, line):

        result = self.decode_data_frame(line)

        if result:
            newstate = self.get_state(result)

            # se tiver novo status, atualiza tudo
            # caso contrario, verifca se esta na hora de atualizar atributos
            if newstate != self.state:
                if self.debug:
                    print("Status: {} => {}".format(self.state, newstate))
                if self.mqtt_client:
                    self.mqtt_client.atualiza_status(newstate)
                    self.mqtt_client.atualiza_atributos(json.dumps(result))
                    self.counter = 0
                self.state = newstate
            else:
                if self.debug:
                    print(result)
                if self.counter >= self.rate:
                    self.counter = 0
                    if self.mqtt_client:
                        self.mqtt_client.atualiza_status(self.state)
                        self.mqtt_client.atualiza_atributos(json.dumps(result))



    def decode_data_frame(self, line):
        '''
        receive a nhs protocol 3 data frame and return a dict with the decoded values
        '''

        decoded = {}
        fmt = '>BcBBBBBBBBBBBBBBBBBB'

        try:
            b = struct.unpack(fmt, b''.join(line))
            decoded['tensao_entrada_rms']  = b[2] + b[3]/100
            decoded['tensao_bateria']      = b[4] + b[5]/100
            decoded['potencia_consumida']  = b[6]
            decoded['tensao_entrada_min']  = b[7] + b[8]/100
            decoded['tensao_entrada_max']  = b[9] + b[10]/100
            decoded['tensao_saida_rms']    = b[11] + b[12]/100
            decoded['temperatura']         = b[13] + b[14]/100
            decoded['corrente_carregador'] = b[15] / 25 * 750
            decoded['status'] = {}
            status = format(b[16], '08b')
            decoded['status']['modo_bateria_ativo'] = status[7]
            decoded['status']['bateria_baixa']      = status[6]
            decoded['status']['falha_de_rede']      = status[5]
            decoded['status']['falha_rapida_rede']  = status[4]
            decoded['status']['entrada_rede_220']   = status[3]
            decoded['status']['saida_nobreak_220']  = status[2]
            decoded['status']['bypass_ativo']       = status[1]
            decoded['status']['carregador_ativo']   = status[0]
        except Exception as e:
            print(e)
            decoded = None

        return(decoded)

    def get_state(self, result):

        if result['status']['falha_de_rede'] == '1':
            state = 'OFF'
        elif result['status']['falha_de_rede'] == '0':
            state = 'ON'
        else:
            state = 'UNKNOW'

        return(state)


if __name__ == "__main__":

    # ler o arquivo de configuracao!
    try:
        if len(sys.argv) > 1:
            configfile = sys.argv[1]
        else:
            configfile = "config.yaml"

        with open(configfile, "r") as ymlfile:
            cfg = yaml.safe_load(ymlfile)

    except Exception as e:
        print("Erro ao tentar abrir arquivo de configuracao: {}".format(configfile))
        print(e)
        sys.exit()

    #inicializa o mqtt caso ele tenha sido configurado
    if 'mqtt' in cfg:
        # inicializa mqtt:
        mqtt_client = MyMQTT(cfg['mqtt']['host'], cfg['mqtt']['port'], cfg['mqtt']['topic'],
                             cfg['mqtt'].get('user'),cfg['mqtt'].get('password') )
    else:
        mqtt_client = None


    mynhs = NHS(cfg['serial']['port'], mqtt_client, cfg.get('mqtt', {}).get('rate', 20), cfg['serial'].get('debug', False))
    mynhs.run_forever()

    sys.exit()

    loop = asyncio.get_event_loop()
    loop.add_reader(s, test_serial, mqtt_client)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        client.loop_stop()
