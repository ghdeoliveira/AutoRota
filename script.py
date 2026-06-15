import requests
import re
import time
from datetime import datetime
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GoogleFormsBotBrilhante2:
    def __init__(self):
        # ENTRIES DO FORMULÁRIO (COMPLETO)
        self.ENTRY_EMAIL = 'emailAddress'  # ← ESPECIAL: não é entry.xxxxx
        self.ENTRY_DRIVER_ID = 'entry.1941002046'
        self.ENTRY_TELEFONE = 'entry.1388004571'
        self.ENTRY_ROTA = 'entry.396510670'
        
        # SEUS DADOS FIXOS
        self.email = 'gho8885@gmail.com'
        self.driver_id = '163347'
        self.telefone = '47996327935'
        
        # URLs
        self.form_id = '1FAIpQLSdUHqCbEnEtmcJgcIiJ0D4RrucqoFfc1Ve-YhPIdUgY4sZnbQ'
        self.view_url = f'https://docs.google.com/forms/d/e/{self.form_id}/viewform'
        self.submit_url = f'https://docs.google.com/forms/d/e/{self.form_id}/formResponse'
        
        # 📋 PALAVRAS-CHAVE EM ORDEM DE PREFERÊNCIA
        self.palavras_prioritarias = [
            'NOVA ESPERANÇA',
            'CEDROS',
            'MONTE ALEGRE',
            'NAÇÕES'
        ]
        
        # 🚫 PALAVRAS PARA BLOQUEAR
        self.palavras_bloqueadas = [
            'BRUSQUE',
            'MOTO',
            'FIORINO',
            'ITAIPAVA',
            'CENTRO'
        ]
        
        self.session = requests.Session()
    
    def buscar_rotas_disponiveis(self):
        """Busca as rotas disponíveis no formulário"""
        try:
            response = self.session.get(self.view_url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            rotas = []
            
            # Busca via FB_PUBLIC_LOAD_DATA_
            fb_match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', html, re.DOTALL)
            if fb_match:
                try:
                    data = json.loads(fb_match.group(1))
                    if data and len(data) > 1 and data[1]:
                        questions = data[1][1] if len(data[1]) > 1 else []
                        for question in questions:
                            if question and len(question) > 4 and question[4]:
                                for opt in question[4]:
                                    if opt and len(opt) > 0:
                                        rota = opt[0] if opt[0] else (opt[1] if len(opt) > 1 else None)
                                        if rota and rota != '.' and rota not in rotas and len(rota) > 2:
                                            rotas.append(rota)
                except Exception as e:
                    logging.debug(f"Erro no FB_DATA: {e}")
            
            # Fallback: busca por data-value
            if not rotas:
                radio_pattern = r'<div[^>]*data-value="([^"]*)"[^>]*role="radio"[^>]*>'
                matches = re.findall(radio_pattern, html)
                for value in matches:
                    if value and value != '.' and value not in rotas and len(value) > 2:
                        rotas.append(value)
            
            rotas = list(dict.fromkeys(rotas))
            
            if rotas:
                logging.info(f"📋 Rotas disponíveis: {len(rotas)}")
                for i, rota in enumerate(rotas, 1):
                    logging.info(f"  {i}. {rota}")
            else:
                logging.warning("⚠️ Nenhuma rota encontrada")
            
            return rotas
            
        except Exception as e:
            logging.error(f"❌ Erro ao buscar rotas: {e}")
            return []
    
    def selecionar_melhor_rota(self, rotas):
        """Seleciona a melhor rota baseada nas palavras"""
        if not rotas:
            return None, None
        
        logging.info("\n🔍 Analisando rotas...")
        
        # Filtra rotas bloqueadas
        rotas_liberadas = []
        for rota in rotas:
            bloqueada = False
            for palavra in self.palavras_bloqueadas:
                if palavra.lower() in rota.lower():
                    logging.info(f"  🚫 BLOQUEADA: {rota} (contém: {palavra})")
                    bloqueada = True
                    break
            if not bloqueada:
                rotas_liberadas.append(rota)
                logging.info(f"  ✅ LIBERADA: {rota}")
        
        if not rotas_liberadas:
            logging.error("❌ Todas as rotas foram bloqueadas!")
            return None, None
        
        # Tenta encontrar rota com palavra prioritária
        for palavra in self.palavras_prioritarias:
            for rota in rotas_liberadas:
                if palavra.lower() in rota.lower():
                    logging.info(f"  🎯 ESCOLHIDA: {rota} (contém: {palavra})")
                    return rota, palavra
        
        # Fallback: primeira rota liberada
        rota = rotas_liberadas[0]
        logging.info(f"  ⚠️ Nenhuma palavra prioritária. Usando primeira: {rota}")
        return rota, None
    
    def pegar_fbzx(self):
        """Captura o token de segurança fbzx"""
        try:
            response = self.session.get(self.view_url, timeout=10)
            match = re.search(r'fbzx" value="([^"]+)"', response.text)
            if match:
                logging.info(f"🔑 Token fbzx capturado")
                return match.group(1)
            return None
        except Exception:
            return None
    
    def enviar_formulario(self, rota):
        """Envia o formulário com a rota escolhida"""
        payload = {
            self.ENTRY_EMAIL: self.email,
            self.ENTRY_DRIVER_ID: self.driver_id,
            self.ENTRY_TELEFONE: self.telefone,
            self.ENTRY_ROTA: rota,
            'fvv': '1',
            'pageHistory': '0'
        }
        
        # Adiciona token de segurança
        fbzx = self.pegar_fbzx()
        if fbzx:
            payload['fbzx'] = fbzx
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = self.session.post(
                self.submit_url,
                data=payload,
                headers=headers,
                allow_redirects=False,
                timeout=30
            )
            
            if response.status_code in [200, 301, 302]:
                logging.info(f"   ✅ SUCESSO! Status: {response.status_code}")
                return True
            else:
                logging.warning(f"   ❌ Falha. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"   ❌ Erro: {e}")
            return False
    
    def enviar(self):
        """Função principal: busca e envia a melhor rota"""
        logging.info("━" * 60)
        logging.info("🚀 BRILHANTE 2 - ENVIO AUTOMÁTICO")
        logging.info(f"📧 Email: {self.email}")
        logging.info(f"✅ Driver ID: {self.driver_id}")
        logging.info(f"📱 Telefone: {self.telefone}")
        logging.info(f"📋 Palavras prioritárias: {self.palavras_prioritarias}")
        logging.info(f"🚫 Palavras bloqueadas: {self.palavras_bloqueadas}")
        logging.info("━" * 60)
        
        # Busca rotas disponíveis
        rotas = self.buscar_rotas_disponiveis()
        
        if not rotas:
            logging.error("❌ Nenhuma rota disponível no momento!")
            return False, None, None
        
        # Seleciona a melhor rota
        rota_escolhida, palavra_match = self.selecionar_melhor_rota(rotas)
        
        if not rota_escolhida:
            logging.error("❌ Nenhuma rota atende aos critérios!")
            return False, None, None
        
        logging.info(f"\n📤 Enviando: \"{rota_escolhida}\"")
        
        # Envia o formulário
        if self.enviar_formulario(rota_escolhida):
            logging.info("\n" + "━" * 60)
            logging.info(f"✅ FORMULÁRIO ENVIADO COM SUCESSO!")
            logging.info(f"📍 Rota: \"{rota_escolhida}\"")
            if palavra_match:
                logging.info(f"🔑 Palavra-chave: \"{palavra_match}\"")
            logging.info(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logging.info("━" * 60)
            return True, rota_escolhida, palavra_match
        else:
            logging.error("❌ Falha no envio!")
            return False, None, None


def enviar():
    """Função de atalho para envio"""
    bot = GoogleFormsBotBrilhante2()
    return bot.enviar()


if __name__ == "__main__":
    enviar()