from flask import Flask, render_template, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from datetime import datetime
import time
import re
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class GoogleFormsBotBrilhante2:
    def __init__(self, email, driver_id, telefone, palavras_prioritarias, palavras_bloqueadas):
        self.email = email
        self.driver_id = driver_id
        self.telefone = telefone
        self.palavras_prioritarias = palavras_prioritarias
        self.palavras_bloqueadas = palavras_bloqueadas
        
        self.form_url = 'https://docs.google.com/forms/d/e/1FAIpQLSdUHqCbEnEtmcJgcIiJ0D4RrucqoFfc1Ve-YhPIdUgY4sZnbQ/viewform'
        
        self.logs = []
        self.driver = None
    
    def add_log(self, message, tipo='info'):
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': message,
            'type': tipo
        }
        self.logs.append(log_entry)
        print(f"[{tipo.upper()}] {message}")
    
    def configurar_driver(self):
        """Configura o ChromeDriver para automação"""
        options = Options()
        
        # Opções para rodar em modo headless (sem abrir janela)
        # options.add_argument('--headless')  # Descomente para rodar em segundo plano
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Mantém a sessão logada
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Caminho para o perfil do Chrome (mantém login)
        # IMPORTANTE: Ajuste o caminho para o seu perfil do Chrome
        user_data_dir = os.path.expanduser('~') + '/AppData/Local/Google/Chrome/User Data'
        options.add_argument(f'--user-data-dir={user_data_dir}')
        options.add_argument('--profile-directory=Default')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.add_log("✅ ChromeDriver configurado com sucesso!", 'success')
            return True
        except Exception as e:
            self.add_log(f"❌ Erro ao configurar ChromeDriver: {e}", 'error')
            self.add_log("💡 Certifique-se que o ChromeDriver está instalado e no PATH", 'warning')
            self.add_log("📥 Baixe em: https://chromedriver.chromium.org/", 'info')
            return False
    
    def buscar_rotas_disponiveis(self):
        """Busca as rotas disponíveis via Selenium"""
        if not self.driver:
            return []
        
        try:
            self.driver.get(self.form_url)
            self.add_log("🔍 Aguardando carregamento do formulário...", 'info')
            
            # Aguarda o formulário carregar
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="radiogroup"]')))
            self.add_log("✅ Formulário carregado!", 'success')
            
            rotas = []
            
            # Busca todas as opções de rota
            opcoes = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="radio"]')
            
            for opcao in opcoes:
                try:
                    # Tenta pegar o data-value ou o texto da opção
                    data_value = opcao.get_attribute('data-value')
                    if data_value and data_value != '.':
                        rotas.append(data_value)
                    else:
                        # Fallback: pega o texto
                        texto = opcao.text.strip()
                        if texto and texto != '.':
                            rotas.append(texto)
                except Exception:
                    pass
            
            # Remove duplicatas
            rotas = list(dict.fromkeys(rotas))
            
            if rotas:
                self.add_log(f"✅ {len(rotas)} rotas encontradas!", 'success')
                for i, rota in enumerate(rotas, 1):
                    self.add_log(f"  {i}. {rota}", 'info')
            else:
                self.add_log("⚠️ Nenhuma rota encontrada!", 'warning')
                # Salva screenshot para debug
                self.driver.save_screenshot('debug_screen.png')
                self.add_log("📸 Screenshot salvo em 'debug_screen.png'", 'info')
            
            return rotas
            
        except TimeoutException:
            self.add_log("❌ Tempo limite excedido ao carregar o formulário!", 'error')
            self.driver.save_screenshot('debug_timeout.png')
            return []
        except Exception as e:
            self.add_log(f"❌ Erro ao buscar rotas: {e}", 'error')
            return []
    
    def selecionar_melhor_rota(self, rotas):
        if not rotas:
            return None
        
        self.add_log("🔍 Analisando rotas disponíveis...", 'info')
        
        rotas_liberadas = []
        for rota in rotas:
            bloqueada = False
            for palavra in self.palavras_bloqueadas:
                if palavra.lower() in rota.lower():
                    self.add_log(f"🚫 BLOQUEADA: {rota} (contém: {palavra})", 'warning')
                    bloqueada = True
                    break
            if not bloqueada:
                rotas_liberadas.append(rota)
                self.add_log(f"✅ LIBERADA: {rota}", 'success')
        
        if not rotas_liberadas:
            self.add_log("❌ Todas as rotas foram bloqueadas!", 'error')
            return None
        
        for palavra in self.palavras_prioritarias:
            for rota in rotas_liberadas:
                if palavra.lower() in rota.lower():
                    self.add_log(f"🎯 ESCOLHIDA: {rota} (contém: {palavra})", 'success')
                    return rota
        
        rota = rotas_liberadas[0]
        self.add_log(f"⚠️ Usando primeira disponível: {rota}", 'warning')
        return rota
    
    def preencher_campos(self, rota):
        """Preenche os campos do formulário"""
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # 1. Preenche o campo de email (se estiver visível)
            try:
                email_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="email"]')))
                email_input.clear()
                email_input.send_keys(self.email)
                self.add_log(f"📧 Email preenchido: {self.email}", 'info')
            except TimeoutException:
                self.add_log("⚠️ Campo de email não encontrado (já está logado?)", 'warning')
            
            # 2. Preenche Driver ID
            try:
                # Busca pelo campo Driver ID
                driver_input = wait.until(EC.presence_of_element_located((By.XPATH, '//span[contains(text(),"ID Driver")]/ancestor::div[contains(@class,"rFrNMe")]//input')))
                driver_input.clear()
                driver_input.send_keys(self.driver_id)
                self.add_log(f"🆔 Driver ID preenchido: {self.driver_id}", 'info')
            except TimeoutException:
                # Tentativa alternativa
                driver_input = self.driver.find_element(By.XPATH, '//input[@aria-labelledby="i5"]')
                driver_input.clear()
                driver_input.send_keys(self.driver_id)
                self.add_log(f"🆔 Driver ID preenchido: {self.driver_id}", 'info')
            
            # 3. Preenche Telefone
            try:
                telefone_input = wait.until(EC.presence_of_element_located((By.XPATH, '//span[contains(text(),"Telefone de contato")]/ancestor::div[contains(@class,"rFrNMe")]//input')))
                telefone_input.clear()
                telefone_input.send_keys(self.telefone)
                self.add_log(f"📱 Telefone preenchido: {self.telefone}", 'info')
            except TimeoutException:
                # Tentativa alternativa
                telefone_input = self.driver.find_element(By.XPATH, '//input[@aria-labelledby="i10"]')
                telefone_input.clear()
                telefone_input.send_keys(self.telefone)
                self.add_log(f"📱 Telefone preenchido: {self.telefone}", 'info')
            
            # 4. Seleciona a rota
            try:
                # Busca a opção da rota pelo texto
                opcoes = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="radio"]')
                for opcao in opcoes:
                    try:
                        # Tenta pegar o data-value ou o texto
                        data_value = opcao.get_attribute('data-value')
                        texto = opcao.text.strip()
                        
                        if data_value == rota or texto == rota or rota in texto:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                            time.sleep(0.5)
                            opcao.click()
                            self.add_log(f"📍 Rota selecionada: {rota}", 'success')
                            break
                    except Exception:
                        continue
            except Exception as e:
                self.add_log(f"❌ Erro ao selecionar rota: {e}", 'error')
                return False
            
            return True
            
        except Exception as e:
            self.add_log(f"❌ Erro ao preencher campos: {e}", 'error')
            return False
    
    def enviar_formulario(self):
        """Clica no botão de enviar"""
        try:
            # Scroll para o botão
            btn_enviar = self.driver.find_element(By.XPATH, '//span[text()="Enviar"]/ancestor::div[@role="button"]')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn_enviar)
            time.sleep(1)
            
            # Clica no botão
            btn_enviar.click()
            self.add_log("📤 Formulário enviado!", 'info')
            
            # Aguarda confirmação
            time.sleep(3)
            
            # Verifica se apareceu a mensagem de sucesso
            try:
                mensagem = self.driver.find_element(By.XPATH, '//div[contains(text(),"Resposta enviada")]')
                if mensagem:
                    self.add_log("✅ CONFIRMAÇÃO: Resposta enviada com sucesso!", 'success')
                    return True
            except:
                # Verifica se há erro
                try:
                    erro = self.driver.find_element(By.XPATH, '//div[contains(text(),"erro") or contains(text(),"problema")]')
                    if erro:
                        self.add_log(f"❌ Mensagem de erro: {erro.text}", 'error')
                        return False
                except:
                    pass
                
                # Pode ser que a confirmação seja em outra página
                if "formResponse" in self.driver.current_url:
                    self.add_log("✅ Redirecionado para página de confirmação!", 'success')
                    return True
                else:
                    self.add_log("⚠️ Status desconhecido, mas o envio pode ter sido bem sucedido", 'warning')
                    return True
            
        except Exception as e:
            self.add_log(f"❌ Erro ao enviar formulário: {e}", 'error')
            self.driver.save_screenshot('debug_envio_erro.png')
            return False
    
    def executar(self):
        """Executa o bot completo com Selenium"""
        self.logs = []
        self.add_log("━" * 50, 'info')
        self.add_log("🚀 Iniciando Brilhante 2 Bot (Selenium)", 'info')
        self.add_log("━" * 50, 'info')
        self.add_log(f"📧 Email: {self.email}", 'info')
        self.add_log(f"🆔 Driver ID: {self.driver_id}", 'info')
        self.add_log(f"📱 Telefone: {self.telefone}", 'info')
        self.add_log(f"🎯 Prioridades: {', '.join(self.palavras_prioritarias)}", 'info')
        self.add_log(f"🚫 Bloqueadas: {', '.join(self.palavras_bloqueadas)}", 'info')
        self.add_log("━" * 50, 'info')
        
        # Configura o driver
        if not self.configurar_driver():
            return {'sucesso': False, 'logs': self.logs}
        
        try:
            # Busca rotas disponíveis
            rotas = self.buscar_rotas_disponiveis()
            
            if not rotas:
                self.add_log("❌ Nenhuma rota disponível no momento!", 'error')
                return {'sucesso': False, 'logs': self.logs}
            
            # Seleciona a melhor rota
            rota_escolhida = self.selecionar_melhor_rota(rotas)
            
            if not rota_escolhida:
                self.add_log("❌ Nenhuma rota atende aos critérios!", 'error')
                return {'sucesso': False, 'logs': self.logs}
            
            # Preenche o formulário
            if not self.preencher_campos(rota_escolhida):
                self.add_log("❌ Falha ao preencher formulário!", 'error')
                return {'sucesso': False, 'logs': self.logs}
            
            # Envia o formulário
            if self.enviar_formulario():
                self.add_log("━" * 50, 'info')
                self.add_log(f"🎉 PROCESSO FINALIZADO COM SUCESSO!", 'success')
                self.add_log(f"📍 Rota: {rota_escolhida}", 'success')
                self.add_log("━" * 50, 'info')
                return {'sucesso': True, 'rota': rota_escolhida, 'logs': self.logs}
            else:
                self.add_log("━" * 50, 'info')
                self.add_log(f"❌ PROCESSO FINALIZADO COM FALHA!", 'error')
                self.add_log("━" * 50, 'info')
                return {'sucesso': False, 'logs': self.logs}
                
        except Exception as e:
            self.add_log(f"❌ Erro inesperado: {e}", 'error')
            return {'sucesso': False, 'logs': self.logs}
        finally:
            # Fecha o navegador
            if self.driver:
                self.driver.quit()
                self.add_log("🔄 Navegador fechado", 'info')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/enviar', methods=['POST'])
def enviar():
    data = request.json
    
    email = data.get('email', 'gho8885@gmail.com')
    driver_id = data.get('driverId', '163347')
    telefone = data.get('telefone', '47996327935')
    palavras_prioritarias = data.get('prioridades', ['CEDROS', 'NOVA ESPERANÇA', 'MONTE ALEGRE', 'NAÇÕES'])
    palavras_bloqueadas = data.get('bloqueadas', ['BOTUVERÁ', 'GUABIRUBA', 'ITAIPAVA', 'BRUSQUE', 'MOTO', 'FIORINO', 'CENTRO'])
    
    bot = GoogleFormsBotBrilhante2(
        email=email,
        driver_id=driver_id,
        telefone=telefone,
        palavras_prioritarias=palavras_prioritarias,
        palavras_bloqueadas=palavras_bloqueadas
    )
    
    resultado = bot.executar()
    return jsonify(resultado)


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Brilhante 2 Bot - Servidor Rodando!")
    print("📍 Acesse: http://localhost:5000")
    print("")
    print("⚠️ IMPORTANTE:")
    print("  1. Certifique-se que o ChromeDriver está instalado")
    print("  2. O navegador vai abrir com sua conta Google já logada")
    print("  3. Aguarde o processo completo")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)