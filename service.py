"""
services.py
Camada de regras de negócio: varredura de rede, download em streaming,
extração estruturada e compactação de release.
"""

from __future__ import annotations
import configparser
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable
import zipfile


class UpdaterService:
    """Concentra as regras de arquivos, rede e manipulação de pacotes de atualização."""

    def __init__(self, config_file: str = "config.ini") -> None:
        self.config = configparser.ConfigParser()
        if not os.path.exists(config_file):
            self._criar_config_padrao(config_file)
        self.config.read(config_file, encoding="utf-8")

        destino_custom = self.config.get("CONFIGURACOES", "destino_base", fallback="").strip()
        if destino_custom:
            self.destino_base = Path(destino_custom)
        else:
            self.destino_base = Path.home() / "Documents" / "Atualiza_Nuvem"

        self.winrar_path = Path(
            self.config.get("CONFIGURACOES", "winrar_path", fallback=r"C:\Program Files\WinRAR\WinRAR.exe")
        )

    def _criar_config_padrao(self, config_file: str) -> None:
        """Gera o arquivo de configurações caso não exista."""
        self.config["CONFIGURACOES"] = {
            "destino_base": "",
            "winrar_path": r"C:\Program Files\WinRAR\WinRAR.exe"
        }
        self.config["REDE"] = {
            "origem_ac": r"\\10.1.254.101\pronto\AC\Portal",
            "origem_ag_nuvem": r"\\10.1.254.101\pronto\AG\Deploy\nuvem",
            "origem_ag_old": r"\\10.1.254.101\pronto\AG\Deploy\old",
            "origem_patrio": r"\\10.1.254.101\pronto\Patrio\Portal"
        }
        with open(config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def listar_versoes(self, sistema: str) -> list[dict[str, str]]:
        """Varre os diretórios da rede e lista as versões disponíveis em ordem decrescente."""
        resultado: list[dict[str, str]] = []

        if sistema == "AC":
            caminho_base = Path(self.config.get("REDE", "origem_ac"))
            if caminho_base.exists():
                for pasta in caminho_base.iterdir():
                    if pasta.is_dir():
                        mtime = pasta.stat().st_mtime
                        resultado.append({
                            "versao": pasta.name,
                            "data": self._formatar_data(mtime),
                            "timestamp": str(mtime)
                        })

        elif sistema == "Patrio":
            caminho_base = Path(self.config.get("REDE", "origem_patrio"))
            if caminho_base.exists():
                for pasta in caminho_base.iterdir():
                    if pasta.is_dir():
                        mtime = pasta.stat().st_mtime
                        resultado.append({
                            "versao": pasta.name,
                            "data": self._formatar_data(mtime),
                            "timestamp": str(mtime)
                        })

        elif sistema == "AG":
            dir_nuvem = Path(self.config.get("REDE", "origem_ag_nuvem"))
            dir_old = Path(self.config.get("REDE", "origem_ag_old"))
            if dir_nuvem.exists() and dir_old.exists():
                for pasta in dir_nuvem.iterdir():
                    if pasta.is_dir():
                        nome_versao = pasta.name
                        exe_old = dir_old / f"FortesAGAtualizador_{nome_versao}.exe"
                        if exe_old.exists():
                            mtime = pasta.stat().st_mtime
                            resultado.append({
                                "versao": nome_versao,
                                "data": self._formatar_data(mtime),
                                "timestamp": str(mtime)
                            })

        resultado.sort(key=lambda x: float(x["timestamp"]), reverse=True)
        return resultado

    def copiar_arquivo_com_progresso(
        self,
        origem: Path,
        destino: Path,
        callback_progresso: Callable[[float], None],
        callback_log: Callable[[str], None]
    ) -> None:
        """Copia arquivo em streaming com buffer de 64KB atualizando a UI."""
        tamanho_total = origem.stat().st_size
        tamanho_mb = tamanho_total / (1024 * 1024)
        callback_log(f">> Baixando: {origem.name} ({tamanho_mb:.2f} MB)...")

        tamanho_bloco = 1024 * 64
        bytes_copiados = 0

        with open(origem, "rb") as f_in, open(destino, "wb") as f_out:
            while True:
                bloco = f_in.read(tamanho_bloco)
                if not bloco:
                    break
                f_out.write(bloco)
                bytes_copiados += len(bloco)
                porcentagem = (bytes_copiados / tamanho_total) * 100
                callback_progresso(porcentagem)

    def processar_download(
        self,
        sistema: str,
        versao: str,
        deseja_descompactar: bool,
        deseja_compactar: bool,
        callback_progresso: Callable[[float], None],
        callback_log: Callable[[str], None]
    ) -> Path:
        """Executa a rotina garantindo integridade dos dados baixados."""
        pasta_versao = self.destino_base / sistema / versao
        pasta_versao.mkdir(parents=True, exist_ok=True)

        pasta_atualiza = pasta_versao / f"Atualiza{sistema}"

        # ---------------------------------------------------------
        # ETAPA 1: DOWNLOAD DOS EXECUTÁVEIS ORIGINAIS
        # ---------------------------------------------------------
        arquivos_instaladores: list[Path] = []
        arquivos_adicionais: list[Path] = []

        if sistema == "AC":
            raiz_ac = Path(self.config.get("REDE", "origem_ac")) / versao
            atualizador_nuvem = raiz_ac / "Nuvem" / "FortesACAtualizadorNuvem.exe"
            ac_nuvem = raiz_ac / "Nuvem" / "AC.exe"
            ac_raiz = raiz_ac / "AC.exe"

            if atualizador_nuvem.exists():
                origem_exe = atualizador_nuvem
            elif ac_nuvem.exists():
                origem_exe = ac_nuvem
                callback_log(">> AtualizadorNuvem ausente. Usando AC.exe da Nuvem.")
            elif ac_raiz.exists():
                origem_exe = ac_raiz
                callback_log(">> Usando AC.exe da raiz.")
            else:
                raise FileNotFoundError(f"Nenhum executável válido encontrado para AC {versao}")

            dest_exe = pasta_versao / origem_exe.name
            self.copiar_arquivo_com_progresso(origem_exe, dest_exe, callback_progresso, callback_log)
            arquivos_instaladores.append(dest_exe)

        elif sistema == "Patrio":
            nome_arquivo = f"FortesPatrioAtualizadorNuvem_{versao}.exe"
            origem = Path(self.config.get("REDE", "origem_patrio")) / versao / "Nuvem" / nome_arquivo
            if not origem.exists():
                raise FileNotFoundError(f"Arquivo {nome_arquivo} não encontrado na rede.")
            dest = pasta_versao / nome_arquivo
            self.copiar_arquivo_com_progresso(origem, dest, callback_progresso, callback_log)
            arquivos_instaladores.append(dest)

        elif sistema == "AG":
            nome_old = f"FortesAGAtualizador_{versao}.exe"
            origem_old = Path(self.config.get("REDE", "origem_ag_old")) / nome_old
            if origem_old.exists():
                dest_old = pasta_versao / nome_old
                self.copiar_arquivo_com_progresso(origem_old, dest_old, callback_progresso, callback_log)
                arquivos_instaladores.append(dest_old)
            else:
                callback_log(f"   [AVISO] Arquivo {nome_old} não foi localizado em 'origem_ag_old'.")

            origem_ag = Path(self.config.get("REDE", "origem_ag_nuvem")) / versao / "AG.exe"
            if origem_ag.exists():
                dest_ag = pasta_versao / "AG.exe"
                self.copiar_arquivo_com_progresso(origem_ag, dest_ag, callback_progresso, callback_log)
                arquivos_adicionais.append(dest_ag)
            else:
                callback_log(f"   [AVISO] AG.exe não localizado em 'origem_ag_nuvem\\{versao}'.")

        # TRAVA DE SEGURANÇA: Se nada foi baixado, interrompe imediatamente!
        if not arquivos_instaladores and not arquivos_adicionais:
            raise FileNotFoundError(
                f"Nenhum arquivo foi transferido da rede para {sistema} versão '{versao}'. "
                "Verifique se o caminho de rede está acessível."
            )

        # ---------------------------------------------------------
        # ETAPA 2: EXTRAÇÃO DO EXECUTÁVEL NA PASTA Atualiza{Sistema}
        # ---------------------------------------------------------
        precisa_extrair = deseja_descompactar or deseja_compactar

        if precisa_extrair:
            pasta_atualiza.mkdir(exist_ok=True)
            callback_log(f">> Extraindo instalador para a pasta \\{pasta_atualiza.name}...")

            for instalador in arquivos_instaladores:
                self._descompactar_com_winrar(instalador, pasta_atualiza, callback_log)

            # Move binários complementares (como o AG.exe) para dentro da pasta extraída
            for extra in arquivos_adicionais:
                destino_extra = pasta_atualiza / extra.name
                shutil.move(str(extra), str(destino_extra))

        # ---------------------------------------------------------
        # ETAPA 3: COMPACTAÇÃO DA PASTA Atualiza{Sistema}
        # ---------------------------------------------------------
        if deseja_compactar:
            callback_log(f">> Compactando pasta \\{pasta_atualiza.name} em formato .rar...")
            self._compactar_pasta(sistema, pasta_atualiza, pasta_versao, callback_log)

        # ---------------------------------------------------------
        # ETAPA 4: LIMPEZA INTELIGENTE
        # ---------------------------------------------------------
        if precisa_extrair:
            callback_log(">> Realizando limpeza dos arquivos temporários...")
            for instalador in arquivos_instaladores:
                try:
                    instalador.unlink(missing_ok=True)
                    callback_log(f"   -> Removido instalador baixado: {instalador.name}")
                except Exception as e:
                    callback_log(f"   [AVISO] Falha ao remover {instalador.name}: {e}")

        # Se não marcou descompactar, remove a pasta solta mantendo apenas o .rar
        if deseja_compactar and not deseja_descompactar:
            try:
                shutil.rmtree(pasta_atualiza, ignore_errors=True)
                callback_log(f"   -> Pasta temporária \\{pasta_atualiza.name} removida.")
            except Exception as e:
                callback_log(f"   [AVISO] Falha ao limpar pasta: {e}")

        callback_log(">> Processo 100% finalizado com sucesso!")
        return pasta_versao

    def _descompactar_com_winrar(self, arquivo_exe: Path, pasta_saida: Path, callback_log: Callable[[str], None]) -> None:
        """Extrai o conteúdo do executável diretamente na pasta de destino."""
        if not self.winrar_path.exists():
            callback_log("   [ERRO] WinRAR não encontrado em C:\\Program Files\\WinRAR\\WinRAR.exe.")
            return

        comando = [
            str(self.winrar_path),
            "x",
            "-ibck",
            "-y",
            str(arquivo_exe),
            str(pasta_saida) + "\\"
        ]

        try:
            res = subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if res.returncode == 0:
                callback_log(f"   -> Conteúdo extraído com sucesso dentro de \\{pasta_saida.name}")
            else:
                callback_log(f"   [AVISO] WinRAR encerrou com código {res.returncode}.")
        except Exception as e:
            callback_log(f"   [ERRO] Falha ao invocar WinRAR: {e}")

    def _compactar_pasta(
        self,
        sistema: str,
        pasta_alvo: Path,
        pasta_destino: Path,
        callback_log: Callable[[str], None]
    ) -> None:
        """Compacta a pasta Atualiza{Sistema} gerando Atualiza{Sistema}.rar."""
        nome_pacote_rar = f"Atualiza{sistema}.rar"
        rar_saida = pasta_destino / nome_pacote_rar

        if self.winrar_path.exists():
            comando = [
                str(self.winrar_path),
                "a",
                "-r",
                "-ibck",
                "-y",
                nome_pacote_rar,
                pasta_alvo.name
            ]

            try:
                res = subprocess.run(
                    comando,
                    cwd=str(pasta_destino),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
                if res.returncode == 0:
                    callback_log(f"   -> Pacote gerado com sucesso: {nome_pacote_rar}")
                    return
                callback_log("   [AVISO] WinRAR retornou erro ao compactar. Tentando ZIP...")
            except Exception as e:
                callback_log(f"   [ERRO] Falha ao acionar compactação WinRAR: {e}")

        # Fallback de segurança em ZIP caso o WinRAR falhe
        zip_saida = pasta_destino / f"Atualiza{sistema}.zip"
        shutil.make_archive(
            base_name=str(pasta_destino / f"Atualiza{sistema}"),
            format="zip",
            root_dir=str(pasta_destino),
            base_dir=pasta_alvo.name
        )
        callback_log(f"   -> Pacote alternativo gerado: {zip_saida.name}")

    @staticmethod
    def _formatar_data(timestamp: float) -> str:
        """Converte timestamp POSIX para formato legível de data e hora."""
        import datetime
        return datetime.datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")