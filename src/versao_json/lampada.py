import socket
import struct
import json
import os
import threading

MULTICAST_GROUP = '224.1.1.5'
MULTCAST_PORT = 5007

GATEWAY_IP=''
GATEWAY_PORT=0

LAMPADA_IP=''
LAMPADA_PORT=0

HEARTBEAT_PORT=0
GATEWAY_HEARTBEAT_PORT=0

LAMP_ID = "lampada-123"
estado_da_lampada='desligado'
cor_da_lampada ='branco'
luminosidade = 50
tamanho_lista_no_gateway=5

def entrar_no_grupo(sock, grp):
    grupo = socket.inet_aton(grp)
    mreq = struct.pack('4sL', grupo, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

def iniciar_lampada():
    global GATEWAY_IP,GATEWAY_PORT,LAMPADA_PORT,LAMPADA_IP,LAMP_ID,HEARTBEAT_PORT,GATEWAY_HEARTBEAT_PORT
    
    # Criando e configurando um socket para o multicast
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MULTCAST_PORT))
    entrar_no_grupo(sock, MULTICAST_GROUP)
    
    #criando e configurando um socket para a lampada
    sock_lampada = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_lampada.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_lampada.bind(('', 0))
    LAMPADA_IP,LAMPADA_PORT=sock_lampada.getsockname()
    LAMPADA_IP = socket.gethostbyname(socket.gethostname())
        
    #criando e configurando um socket para o heartbeat
    sock_heartbeat = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_heartbeat.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_heartbeat.bind(('', 0))
    LAMPADA_IP,HEARTBEAT_PORT=sock_heartbeat.getsockname()
    LAMPADA_IP = socket.gethostbyname(socket.gethostname())
    
    print(f"Lâmpada {LAMP_ID} escutando no endereço multicast {MULTICAST_GROUP}:{MULTCAST_PORT}")
    
    ouvindo_multicast(sock)
    
    t_ouvir_heartbeat = threading.Thread(target= ouvindo_heartbeat,args=(sock_heartbeat,sock))
    t_ouvir_heartbeat.start()

    aguardando_comandos(sock_lampada)
    
    t_ouvir_heartbeat.join()

def ouvindo_heartbeat(sock_heartbeat,sock):
    global GATEWAY_IP,GATEWAY_PORT,LAMPADA_PORT,LAMPADA_IP,LAMP_ID,HEARTBEAT_PORT,GATEWAY_HEARTBEAT_PORT,tamanho_lista_no_gateway
    while True:
        try:
            sock_heartbeat.settimeout(tamanho_lista_no_gateway)
            dados, endereco = sock_heartbeat.recvfrom(1024)
            mensagem_json = json.loads(dados.decode('utf-8'))
            
            if mensagem_json.get("comando") == "heartbeat":
                tamanho_lista_no_gateway=5 + ( 5 * ( int(mensagem_json.get("tamanho_lista")) ) )
                resposta_json = {"tipo":"heartbeat","heartbeat_port":f"{HEARTBEAT_PORT}"}
                GATEWAY_HEARTBEAT_PORT=int(GATEWAY_HEARTBEAT_PORT)
                sock_heartbeat.sendto(json.dumps(resposta_json).encode('utf-8'), (GATEWAY_IP,GATEWAY_HEARTBEAT_PORT))

        except TimeoutError:
                ouvindo_multicast(sock)
                        
def ouvindo_multicast(sock):
    global GATEWAY_IP,GATEWAY_PORT,LAMPADA_PORT,LAMP_ID,LAMPADA_IP,HEARTBEAT_PORT,GATEWAY_HEARTBEAT_PORT
    print(f"Lâmpada {LAMP_ID} escutando no endereço multicast {MULTICAST_GROUP}:{MULTCAST_PORT}")
    while True:
        dados, endereco = sock.recvfrom(1024)
        mensagem_json = json.loads(dados.decode('utf-8'))
        
        print(f"Mensagem recebida de {endereco}: {mensagem_json}")
        if mensagem_json.get("comando") == "descobrir":
            resposta_json = {"tipo":"descoberta",
                             "nome":"lampada",
                             "id": LAMP_ID,
                             "status": "pronto",
                             "endereco":[f"{LAMPADA_IP}",f"{LAMPADA_PORT}"],
                             "heartbeat_port":f"{HEARTBEAT_PORT}",
                             "funcionalidades": [ {"nome":"ligar/desligar","parametros":[]},
                                                 {"nome":"brilho","parametros":[{"nome":"valor do brilho","tipo":"int"}]},
                                                 {"nome":"cor","parametros":[{"nome":"cor da lâmpada","tipo":"vermelho,verde,amarelo,azul,branco,roxo"}]}
                                                ]
                             }
            endereco_completo_do_gateway=mensagem_json.get("enderecoGateway")
            GATEWAY_IP, GATEWAY_PORT = endereco_completo_do_gateway
            GATEWAY_PORT = int(GATEWAY_PORT)
            GATEWAY_HEARTBEAT_PORT=mensagem_json.get("gateway_heartbeat_port")
            sock.sendto(json.dumps(resposta_json).encode('utf-8'), (GATEWAY_IP,GATEWAY_PORT))
            print(f"Respondendo ao gateway {endereco_completo_do_gateway}")
            break

def aguardando_comandos(sock_lampada):
    global GATEWAY_IP, GATEWAY_PORT,LAMP_ID,estado_da_lampada,cor_da_lampada,luminosidade
    while True:
        dados, endereco = sock_lampada.recvfrom(1024)
        mensagem_json = json.loads(dados.decode('utf-8'))
        print(f"Mensagem recebida de {endereco}: {mensagem_json}")
        
        if mensagem_json.get("comando") == "ligar/desligar":
            os.system("cls")
            ligar_desligar()
            mostrar_status()
            resposta_json = {
                "status":[
                    {"tipo":"atualização"},{"nome":"lampada"},{"id":f"{LAMP_ID}"},
                    {"estado da lampada": f"{estado_da_lampada}"},{"cor da lampada": f"{cor_da_lampada}"}
                     ,{"luminosidade": luminosidade}]
                }
            
            sock_lampada.sendto(json.dumps(resposta_json).encode('utf-8'), (GATEWAY_IP,GATEWAY_PORT))
            print(f"Atualizando o status da lampada para o gateway")
       
        elif mensagem_json.get("comando")=="brilho":
            os.system("cls")
            brilho(int(mensagem_json.get("parametros")[0]))
            mostrar_status()
            resposta_json = {
                "status":[
                    {"tipo":"atualização"},{"nome":"lampada"},{"id":f"{LAMP_ID}"},
                    {"estado da lampada": f"{estado_da_lampada}"},{"cor da lampada": f"{cor_da_lampada}"}
                     ,{"luminosidade": luminosidade}]
                }
            
            sock_lampada.sendto(json.dumps(resposta_json).encode('utf-8'), (GATEWAY_IP,GATEWAY_PORT))
            print(f"Atualizando o status da lampada para o gateway")   
       
        elif mensagem_json.get("comando")=="cor":
            os.system("cls")
            cor(mensagem_json.get("parametros")[0])
            mostrar_status()
            resposta_json = {
                "status":[
                    {"tipo":"atualização"},{"nome":"lampada"},{"id":f"{LAMP_ID}"},
                    {"estado da lampada": f"{estado_da_lampada}"},{"cor da lampada": f"{cor_da_lampada}"}
                     ,{"luminosidade": luminosidade}]
                }
            sock_lampada.sendto(json.dumps(resposta_json).encode('utf-8'), (GATEWAY_IP,GATEWAY_PORT))
            print(f"Atualizando o status da lampada para o gateway")
        
        elif mensagem_json.get("comando")=="status":
            os.system("cls")
            mostrar_status()
            resposta_json = {
                "status":[
                    {"tipo":"atualização"},{"nome":"lampada"},{"id":f"{LAMP_ID}"},
                    {"estado da lampada": f"{estado_da_lampada}"},{"cor da lampada": f"{cor_da_lampada}"}
                     ,{"luminosidade": luminosidade}]
                }
            sock_lampada.sendto(json.dumps(resposta_json).encode('utf-8'), (GATEWAY_IP,GATEWAY_PORT))
            print(f"Atualizando o status da lampada para o gateway") 
        
        elif mensagem_json.get("comando")=="renomear":
            os.system("cls")
            LAMP_ID=mensagem_json.get("novo_id")
            mostrar_status()
            resposta_json = {
                "status":[
                    {"tipo":"atualização"},{"nome":"lampada"},{"id":f"{LAMP_ID}"},
                    {"estado da lampada": f"{estado_da_lampada}"},{"cor da lampada": f"{cor_da_lampada}"}
                    ,{"luminosidade": luminosidade}]
                }
            sock_lampada.sendto(json.dumps(resposta_json).encode('utf-8'), (GATEWAY_IP,GATEWAY_PORT))
            print(f"Atualizando o status da lampada para o gateway")   

#funcionalidades da lampada  

def ligar_desligar():
    global estado_da_lampada
    if estado_da_lampada == 'desligado':
        estado_da_lampada='ligado'
    else:
        estado_da_lampada = 'desligado'

def brilho(valor_do_brilho):
    global luminosidade
    if valor_do_brilho>=0 and valor_do_brilho<=100:
        luminosidade = valor_do_brilho
    else:
        print("o valor de brilho não é válido")

def cor(cor_escolhida):
    global cor_da_lampada
    cor_da_lampada=cor_escolhida
       
def mostrar_status():
    global LAMP_ID,estado_da_lampada,cor_da_lampada,luminosidade
    print(f"id:{LAMP_ID}")
    print(f"estado:{estado_da_lampada}")
    print(f"cor:{cor_da_lampada}")
    print(f"luminosidade:{luminosidade}")

if __name__ == "__main__":
    print("Digite o nome da lampada:\n")
    LAMP_ID=input()
    iniciar_lampada()
    
