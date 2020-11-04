import socket
import pickle
import time
import codecs
import sys
import random
import threading
import copy
import os

#Definiciok
verzio = '1.0.0'
datum_modified = '2020/10/31'
modul_nev = 'Intranet I/O vezerlo'
level = 2 #kozep kritikus
Errors = 0
#
MAX_MSG_LENGTH = 110
#
SERVER_TIMEOUT = 0.01


#IO osztalyok================================================================================
#1.Vonal vezerlo obiektumok
class Indicators:
    #Sajat obiektumok====================================
    class State:
        def __init__(this):  
            #Indicators
            this.Feszultseg = 143
            this.Aram = 12.37
            this.Teljesitmeny = this.Feszultseg*this.Aram
            this.Kapcsolo_allapot = 1 #0-nyitva, 1-zarva
            this.Aram_irany = 1 #0-be, 1-ki
            #Hiba jelzok 0->nincs baj, 1->figyelmeztetes, 2->kritikus allapot
            this.FeszultsegERR = 1
            this.AramERR = 0
            this.TeljesitmenyERR = 2
    #====================================================
    def __init__(this):
        this.States = []
        for i in range(0, 19):
            this.States.append(this.State())
        this.Vonal_Feszultseg = 0
        this.Kapcsolat = 0 #Szerverhez csatlakozva: 0->Nem, 1->Igen
        this.Felulirva = False #Kapcsolok felulirva: 0->Kapcsolok tiltva, 1->Kapcsolok engedelyezve
class Controls:
    def __init__(this):
        this.Kapcsolo_parancs = [] #0-nyitas, 1-zaras
        this.Feluliro_parancs = []
        for i in range(19):
            this.Kapcsolo_parancs.append(0)
            this.Feluliro_parancs.append(0)
#=============================================================================================
#2.Terminal vezerlo obiektumok

#=============================================================================================

class Log:
    class szinek:
        OK = '\033[92m'
        FIGYELMEZTETES = '\033[93m'
        HIBA = '\033[91m'
        SEMLEGES = '\033[0m'
        
    def __init__(this):
       #Konstansok
        this.messages = []
        this.MAX_LENGTH = 1024
       #Thread cuccok
        this.lock_in = threading.Lock()
        this.lock_out = threading.Lock()
        this.messageLock = threading.Lock()
        os.system("") #Enelkul nem mukodnek a szinek
        
    def log(this, name, msg, error): #error: 0-[OK], 1-[ERROR], 2,3,...-semmi
        with this.lock_in:
            if error == 0: #[OK]
                ERROR = f'{this.szinek.OK}[OK]{this.szinek.SEMLEGES}'
            elif error == 1: #[ERROR]
                ERROR = f'{this.szinek.HIBA}[ERROR]{this.szinek.SEMLEGES}'
            else:
                ERROR = ''
          #uzenetek hozzaferes    
            this.messageLock.acquire()
            try:
                this.messages.append(f'[ImreApp]->[{name}]: {msg}'.ljust(MAX_MSG_LENGTH) + f'{ERROR}')
            finally:
                this.messageLock.release()
          #uzenetek kiiras    
            print(this.messages[len(this.messages)-1])
            this.Update()
            
    def download(this):
        with this.lock_out:
            msg_download = b''
            this.messageLock.acquire()
            try:
                msg_download = pickle.loads(this.messages)
            finally:
                this.messageLock.release()
            return msg_download
        
    def Update(this):
        if len(this.messages) > this.MAX_LENGTH: #Nincs tobb hely loggolni => torlodnek a legelso bejegyzesek
            this.messageLock.acquire()
            try:
                this.messages.pop(0)
            finally:
                this.messageLock.release()

class VonalKezelo(threading.Thread):

   #Sajat obiektumok
    class Buffer:
        def __init__(this, socket, address, input_data, output_data):
            this.socket = socket
            this.address = address
            this.input_data = input_data
            this.output_data = output_data
            this.errorCount = 0
    
    def __init__(this, logger):
        try:
        #sajat cuccok
            this.nev = 'Vonal kezelo'
        #thread init
            threading.Thread.__init__(this)
            this.check = threading.Thread(target=this.CheckClients)
            this.stop = False
        #IO cuccok init
            this.jegyzokonyv = logger
            this.log(this.nev, 'Kliens ellenorzo szal elinditva', 0)
            this.indicators = Indicators()
            this.controls = Controls()
        #server init
            this.ADDRESS = 'localhost'
            this.PORT = 10000
            this.ERROR_KUSZOB = 3
            this.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            this.server.bind((this.ADDRESS, this.PORT))
            this.server.listen(5) #max 5 kliens csatlakozhat egyszerre
           #IO vezerlok
            this.buffer = [] #Kliensek + IP_cim + bejovo_adat + kimeno_adat + hibak_szama
        #Minden OK    
            this.log(this.nev, f'Szerver elinditva a {this.PORT} porton', 0)
        except OSError:
            this.log(this.nev, 'Mar fut egy szerver ezen a porton.', 1)
            this.log(this.nev, 'A szerver leall...', 2)
            this.stop = True
        except:
            this.log(this.nev, 'Hiba a szerver inditasanal:', 1)
            print(sys.exc_info())
            this.log(this.nev, 'A szerver leall...', 2)
            this.stop = True
        
    def Kikapcs(this):
        try:
            this.log(this.nev, '============================', 2)
            this.log(this.nev, 'Szerver leallitasa...', 2)
            this.log(this.nev, '1. Kapcsolat levalasztasa...', 2)
            this.server.close()
            this.log(this.nev, 'Kapcsolat levalasztva', 0)
            this.log(this.nev, '2. Szalak leallitasa leallitasa...', 2)
            this.log(this.nev, 'Szalak leallitva', 0)
            this.log(this.nev, '3. Buffer obiektumok torlese...', 2)
            this.buffer = []
            this.log(this.nev, 'Bufferek torolve', 0)
            this.log(this.nev, "Szerver leallitva.", 0)
            this.log(this.nev, '============================', 2)
        except:
            pass
    
    def CheckClients(this):
        try:
            while True:
                i = 0
                buffer_length = len(this.buffer)
                while i < buffer_length:
                  #Kliens ellenorzese (ha mar voltak hibak akkor )
                    if this.buffer[i].errorCount >= this.ERROR_KUSZOB: #Lehetetlen kommunikalni a klienssel
                        try:
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Lecsatlakoztatas...', 2)
                            #this.logger.log(this.nev, '', 2)
                            this.buffer[i].socket.close() #Kliens bezarasa
                        except:
                            pass
                        this.buffer.pop(i) #Kliens eltavolitasa a listarol
                        buffer_length = buffer_length - 1
                        this.log(this.nev, '[Kommunikacio]: Lecsatlakozva', 0)
                    else: #A kliens rendben van => kommunikacio megkezdese
                  #Fogad
                        try:
                            msg_in = this.buffer[i].socket.recv(2048) #adat fogadas
                        except:
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Adatfogadasi hiba', 1)
                            this.buffer[i].errorCount = this.buffer[i].errorCount + 1
                            msg_in = b''
                        try: #Dekodolas
                            data_in = pickle.loads(msg_in)
                        except:
                            data_in = this.buffer[i].input_data #az elozo erteket tolti be
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Dekodolasi hiba', 1)
                        if isinstance(data_in, Controls):
                            this.buffer[i].input_data = data_in
                        else:
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Ertelmezhetetlen bejovo adat', 1)
                      #Kuld
                        try:
                            msg_out = pickle.dumps(this.buffer[i].output_data) #Adat kodolas
                        except:
                            msg_out = Indicators()
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Kodolasi hiba', 1)
                        try:
                            this.buffer[i].socket.send(msg_out)
                        except:
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Adatkuldesi hiba', 1)
                            this.buffer[i].errorCount = this.buffer[i].errorCount + 1
                    i = i + 1
                #
                time.sleep(0.01)
                if this.stop:
                    this.log(this.nev, 'Kliensfigyelo modul leallt', 0)
                    return
        except:
            this.log(this.nev, 'Helyrehozhatatlan hiba a kliens ellenorzoknel. Leallas...', 1)
            try:
                del this
            except:
                pass
        
    def log(this, nev, uzenet, hibakod):
        try:
            this.jegyzokonyv.log(nev, uzenet, hibakod)
        except: #a naplozas nem mukodik
            print(f'[ImreApp]->{this.nev} {uzenet}, hibakod: {hibakod}')
    
    def run(this):
        try:
            this.log(this.nev, 'Klienskezelo modul inditasa...', 2)
            try:
                this.check.start()
            except:
                this.log(this.nev, 'Nem lehet uj szalat inditani a klienskezelonek', 1)
                print(sys.exc_info())
                return 1
            this.server.settimeout(0.01)
            this.log(this.nev, 'Klienskezelo modul elinditva', 0)
            while True:
                if this.stop:
                    this.log(this.nev, 'Szerver csatlakozaskezelo modul leallitva', 0)
                    return
                try:
                    TempClient, TempAddr = this.server.accept() #Varakozas csatlakozasra
                    print('')
                    this.log(this.nev, f'{TempAddr} csatlakozva a szerverre', 0)
                    #TempClient.settimeout(TIMEOUT)
                    this.buffer.append(this.Buffer(TempClient, TempAddr, Controls(), Indicators()))
                except:
                    pass
                time.sleep(1)
        except:
            print(sys.exc_info())
            this.log(this.nev, 'Helyrehozhatatlan hiba az elso lepesnel', 1)
            this.log(this.nev, 'A vonalkezelo leall...', 2)
            try:
                this.Kikapcs()
            except:
                pass
            
class MainController(threading.Thread):
    def __init__(this, logger):
        try:
          #Sajat obiektumok
            this.logger = logger
          #thread init
            threading.Thread.__init__(this)
        except:
            pass

    def Control(this):
        pass

    def run(this):
        this.log('Automata vezerlo', 'elindult', 0)
    
    def log(this, nev, uzenet, hibakod):
        try:
            this.logger.log(nev, uzenet, hibakod)
        except:
            pass

    def Kikapcs(this):
        this.log(this.nev, 'Automata evzerlo modul leallitasa...', 2)
        this.log(this.nev, 'Leallitva', 0)
            
class Terminal(threading.Thread):

   #Sajat obiektumok
    class Uzenetek:
        alap = f"""[ImreApp] Modul: Terminal
[ImreApp] Verzio: {verzio}
[Imreapp] Utolso modositas datuma: {datum_modified}
[ImreApp] Kritikussagi szint: 3
[ImreApp] Kritikus hibak szama: {Errors}
                """
        help_uzenet = "help uzenet...(fejlesztes alatt)"
                        
    class Buffer:
        def __init__(this, socket, address):
            this.socket = socket
            this.address = address
            this.input_data = ""
            this.output_data = [Terminal.Uzenetek.alap]
            this.errorCount = 0
    
    def __init__(this, logger):
        try:
        #sajat cuccok
            this.nev = 'Terminal vezerlo'
            this.prompt = "ImreApp]->Terminal:-$"
        #thread init
            threading.Thread.__init__(this)
            this.check = threading.Thread(target=this.CheckClients)
        #IO cuccok init
            this.jegyzokonyv = logger
            this.log(this.nev, 'Kliens ellenorzo szal elinditva', 0)
            this.indicators = Indicators()
            this.controls = Controls()
        #server init
            this.ADDRESS = 'localhost'
            this.PORT = 10001
            this.ERROR_KUSZOB = 3
            this.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            this.server.bind((this.ADDRESS, this.PORT))
            this.server.listen(5) #max 5 kliens csatlakozhat egyszerre
           #IO vezerlok
            this.buffer = [] #Kliensek + IP_cim + bejovo_adat + kimeno_adat + hibak_szama
        #Minden OK    
            this.log(this.nev, f'Szerver elinditva a {this.PORT} porton', 0)
        except:
            print(sys.exc_info())
        
    def Kikapcs(this):
        try:
            this.log(this.nev, '============================', 2)
            this.log(this.nev, 'Szerver leallitasa...', 2)
            this.log(this.nev, '1. Szalak leallitasa leallitasa...', 2)
            try:
                this.check.stop()
                this.stop()
            except:
                this.log(this.nev, 'Hiba a szalak leallitasanal', 1)
            this.log(this.nev, '2. Buffer obiektumok torlese...', 2)
            this.buffer = []
            this.log(this.nev, 'Szerver leallitva', 0)
            this.log(this.nev, '============================', 2)
        except:
            pass
            
    def Ertelmez(this, n):
        global vonalController
        global jegyzokonyv
        global automata
        global SzerverLeall
        
        try:
            #print(this.buffer[i].input_data)
            command = this.buffer[n].input_data.split()
            eredmeny = ''
          #parancs ertelmezese es vegrehajtasa
            if command[0] == 'nope': #ures uzenet
                eredmeny = ''
            elif command[0] == 'kilep': #App teljes leallas
                SzerverLeall = True
            elif command[0] == 'belepes':
                eredmeny = ''
            elif command[0] == 'help':
                eredmeny = Terminal.Uzenetek.help_uzenet
            elif command[0] == 'vonal':
                if command[1] == 'indit':
                    eredmeny = 'Vonalkezelo inditasa...\n'
                    try:
                        vonalController = VonalKezelo(this.jegyzokonyv)
                        vonalController.start()
                        eredmeny = eredmeny + 'VonalKezelo elinditva'.ljust(MAX_MSG_LENGTH) + '[OK]'
                    except:
                        eredmeny = eredmeny + 'Vonalkezelot nem lehet elinditani'.ljust(MAX_MSG_LENGTH) + 'ERR'
                elif command[1] == 'leall':
                    eredmeny = 'Vonalkezelo leallitasa...\n'
                    try:
                        vonalController.Kikapcs()
                        time.sleep(0.05)
                        del vonalController
                    except:
                        pass
                    eredmeny = eredmeny + 'Vonalkezelo leallitva'.ljust(MAX_MSG_LENGTH) + '[OK]'
                else:
                    eredmeny = 'indit  leall'
            else: #Ervenhytelen parancs
                eredmeny = 'Ervenytelen parancs'
                
                
            this.buffer[n].output_data = [eredmeny]
        except:
            try:
                this.log(this.nev, f'Terminal parancs ertelmezesi hiba: "{this.buffer[n].input_data.split()[0]}"', 1)
                this.buffer[n].output_data = ['[ImreERR] hiba a parancs vegrehajtasanal '.ljust(MAX_MSG_LENGTH)+'[ERR]']
                print(sys.exc_info())
            except:
                pass
    
    def CheckClients(this):
        try:
            while True:
                i = 0
                buffer_length = len(this.buffer)
                while i < buffer_length:
                  #Kliens ellenorzese (ha mar voltak hibak akkor )
                    if this.buffer[i].errorCount >= this.ERROR_KUSZOB: #Lehetetlen kommunikalni a klienssel
                        try:
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Lecsatlakoztatas...', 2)
                            #this.logger.log(this.nev, '', 2)
                            this.buffer[i].socket.close() #Kliens bezarasa
                        except:
                            pass
                        this.buffer.pop(i) #Kliens eltavolitasa a listarol
                        buffer_length = buffer_length - 1
                        this.log(this.nev, '[Kommunikacio]: Lecsatlakozva', 0)
                    else: #A kliens rendben van => kommunikacio megkezdese
                  #Fogad
                        try:
                            msg_in = this.buffer[i].socket.recv(2048) #adat fogadas
                        except:
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Adatfogadasi hiba', 1)
                            msg_in = b''
                            this.buffer[i].errorCount = this.buffer[i].errorCount + 1
                        try: #Dekodolas
                            data_in = msg_in.decode('utf-8')
                            this.buffer[i].input_data = data_in
                        except:
                            data_in = this.buffer[i].input_data #az elozo erteket tolti be
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Dekodolasi hiba', 1)
                  #Bejovo adatok ertelmezese es kimeno adat generalasa
                        this.Ertelmez(i)
                  #Kuld
                        try:
                            msg_out = pickle.dumps(this.buffer[i].output_data) #Adat kodolas
                        except:
                            msg_out = b''
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Kodolasi hiba', 1)
                        try:
                            this.buffer[i].socket.send(msg_out)
                        except:
                            this.log(this.nev, f'[Kommunikacio]: Kliens #{this.buffer[i].address}: Adatkuldesi hiba', 1)
                            this.buffer[i].errorCount = this.buffer[i].errorCount + 1
                    i = i + 1
                #
                time.sleep(0.01)
        except:
            this.log(this.nev, 'Helyrehozhatatlan hiba a kliens ellenorzoknel. Leallas...', 1)
            try:
                del this
            except:
                pass
        
    def log(this, nev, uzenet, hibakod):
        try:
            this.jegyzokonyv.log(nev, uzenet, hibakod)
        except: #a naplozas nem mukodik
            print(f'[ImreApp]->{this.nev} {uzenet}, hibakod: {hibakod}')
    
    def run(this):
        try:
          #Init
            this.log(this.nev, 'Terminal modul inditasa...', 2)
            try:
                this.check.start()
            except:
                this.log(this.nev, 'Nem lehet uj szalat inditani a terminal vezerlonek', 1)
                print(sys.exc_info())
                return 1
            this.server.settimeout(SERVER_TIMEOUT)
            this.log(this.nev, 'Kliens figyelo szal elinditva elinditva', 0)
            this.log(this.nev, 'Terminal modul elinditva', 0)
          #Periodikus
            while True:
                try:
                    TempClient, TempAddr = this.server.accept() #Varakozas csatlakozasra
                    print('')
                    this.log(this.nev, f'{TempAddr} csatlakozva a szerverre', 0)
                    this.buffer.append(this.Buffer(TempClient, TempAddr))
                except:
                    pass
                time.sleep(1)
        except:
            print(sys.exc_info())
            this.log(this.nev, 'Helyrehozhatatlan hiba az elso lepesnel', 1)
            this.log(this.nev, 'Terminal vezerlo leall...', 2)
            this.log(this.nev, 'Javaslott a szerver teljes ujrainditasa:', 2)
            this.log(this.nev, ' (Terminal modul nelkul nem lehet hozzaferni a szerverhez)', 2)
            try:
                del this
            except:
                pass

#======================================================================================================
#Teszt resz

#======================================================================================================
#Fo szal
print('=============================================================')
print(f'[ImreApp] Verzio: {verzio}')
print(f'[Imreapp] Utolso modositas datuma: {datum_modified}')
print(f'[ImreApp] Szerep: {modul_nev}')
print(f'[ImreApp] Modul kritikussagi szint: {level}')
print(f'[ImreApp] Kritikus hibak szama: {Errors}')
print('=============================================================')
print('')
print('')
print('[ImreApp] Modulok inditasa...')

#1. I/O modul inditasa
time.sleep(0.1)
print('')
print('[ImreApp] #1. I/O modul inditasa...')
try:
    jegyzokonyv = Log()
except:
    print('[ImreApp] Sulyos rendszerhiba az I/O vezerlovel.')
    print('[ImreApp] Problema lehetseges oka:')
    print('')
    print(f'   {sys.exc_info()}')
    print('')
    try:
        jegyzokonyv = Log()
    except:
        print('[ImreERR] Nem lehet helyrehozni az I/O modult. Kilepes...')
        print('[ImreINFO] Lehetseges megoldas: Hivd Imret')
        exit(1)
    jegyzokonyv.log('Foszal', 'Problema megoldva', 0)

#2. Vonal vezerlo inditasa
time.sleep(0.1)
print('')
print('[ImreApp] #2. 230V fovonal kezelo modul inditasa...')
#vonalController = VonalKezelo(jegyzokonyv) ### Teszt hiba generator: letrehoz egy szervert ezen a porton igy majd a vonalkezelo errort ad ###
try:
    vonalController = VonalKezelo(jegyzokonyv)
    vonalController.start()
except:
    print('[ImreApp] Sulyos rendszerhiba a vonal vezerlovel.')
    print('[ImreApp] Problema lehetseges oka:')
    print('')
    print(f'   {sys.exc_info()}')
    print('')
    print('          vagy:')
    print('')
    print('    Mar meg van nyitva egy vonalkezelo szerver ezen a porton')
    print('')
    print('')
    try:
        vonalController = VonalKezelo(jegyzokonyv)
        vonalController.start()
        jegyzokonyv.log('Vonal vezerlo', 'Problema megoldva', 0)
    except:
        print('[ImreERR] Nem lehet helyrehozni a vonal kezelo modult.')
        print('[ImreERR] A hiba nem kritikus, a program folytatodik')
        print('[ImreERR] A vonalkezelo kezileg is elindithato a terminalbol:')
        print('    "vonalkezelo ujraindit"')
        print('[ImreINFO] Lehetseges megoldas: Hivd Imret')


#3. Fovezerlo inditasa
time.sleep(0.1)
print('')
print('[ImreApp] #3. Automata iranyitorendszer modul inditasa...')
try:
    automata = MainController(jegyzokonyv)
    automata.start()
except:
    print('[ImreApp] Az automata rendszert nem lehet elinditani')
    print('[ImreApp] Problema lehetseges oka:')
    print('')
    print(f'   {sys.exc_info()}')
    print('')
    print('          vagy:')
    print('')
    print('    * Valamelyik iranyito parameter ervenytelen')
    print('    * Egy masik modul(I/O) sulyos rendszerhibat okozott amely')
    print('      megvaltoztatta az I/O obiektumokat')
    print('    * az I/O obiektumok helytelenul lettek letrehozva')
    print('')
    print('[ImreApp] Ujrainditas megkiserlese...')
    try:
        automata = MainController(jegyzokonyv)
        automata.start()
        jegyzokonyv.log('[ImreApp]', 'Problema megoldva', 0)
    except:
        print('[ImreERR] Nem lehet helyrehozni az iranyito modult.')
        print('[ImreERR] A hiba nem kritikus, a program folytatodik automata vezerles nelkul')
        print('[ImreERR] Az automata vezerlo modul kezileg is elindithato a terminalbol:')
        print('    "controller ujraindit"')
        print('[ImreINFO] Lehetseges megoldas: Hivd Imret')
        
#4. Terminal inditasa
time.sleep(0.1)
print('')        
print('[ImreApp] #4. Terminal kezelo modul inditasa')
try:
    terminal = Terminal(jegyzokonyv)
    terminal.start()
except:
    print('[ImreApp] A terminal modult nem lehet elinditani')
    print('[ImreApp] Problema lehetseges oka:')
    print('')
    print(f'   {sys.exc_info()}')
    print('')
    print('          vagy:')
    print('')
    print('    * Mar fut egy szerver ez alatt a port alatt')
    print('    * az I/O obiektumok helytelenul lettek letrehozva')
    print('')
    print('[ImreApp] Ujrainditas megkiserlese...')
    try:
        terminal = Terminal(jegyzokonyv)
        terminal.start()
        jegyzokonyv.log('[ImreApp]', 'Problema megoldva', 0)
    except:
        print('[ImreERR] Nem lehet helyrehozni a terminal modult.')
        print('[ImreERR] A hiba nem kritikus, a program folytatodik terminal nelkul')
        print('[ImreINFO] Lehetseges megoldas: Hivd Imret')



SzerverLeall = False

while True:
    if SzerverLeall:
       #1. Terminal leallitas
        time.sleep(0.25)
        try:
            terminal.Kikapcs()
        except:
            pass
       #2. Automata vezerles leallitas
        time.sleep(0.25)
        try:
            automata.Kikapcs()
        except:
            pass
       #3. Vonal vezerles leallitas
        time.sleep(0.25)
        try:
            vonalController.Kikapcs()
        except:
            pass
        print("[ImreApp] App leall...")
        break;

os._exit(0)