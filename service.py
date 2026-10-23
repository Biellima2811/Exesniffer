"""
services.py
Módulo isolado para operações de I/O de arquivos de rede e compactação.
"""

from __future__ import annotations
import configparser
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable
import zipfile
import datetime

from coverage import data


class UpdaterService:
    """Concentra a lógica de busca e transferência de atualizadores."""
    def __init__(self, config_file: str = "config.ini") -> None:
        self.config = configparser.ConfigParser()
        if not os.path.exists(config_file):
            self.criar_config_padrao(config_file)
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
        """Gera um arquivo de configuração caso não exista."""
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
        """
        Escaneia as pastas de rede do sistema escolhido e retorna uma lista
        de versões disponíveis com data de modificação, da mais nova para a mais antiga.
        """

        resultado: list[dict[str, str]] = []

        if sistema == "AC":
            caminho_base = Path(self.config.get("REDE", "origem_ac"))
            if caminho_base.exists():
                for pasta in caminho_base.iterdir():
                    mtime = pasta.stat().st_mtime
                    resultado.append({
                        "versao" : pasta.name,
                        "data" : self._formatar_data(mtime),
                        "timestamp" : str(mtime)
                    })

        elif sistema == "Patrio":
            caminho_base = Path(self.config.get("REDE", "origem_patrio"))
            if caminho_base.exists():
                for pasta in caminho_base.iterdir():
                    mtime = pasta.stat().st_mtime
                    resultado.append({
                        "versao" : pasta.name,
                        "data" : self._formatar_data(mtime),
                        "timestamp" : str(mtime)
                    })
        elif sistema == "AG":
            dir_nuvem = Path(self.config.get("REDE", "origem_ag_nuvem"))
            dir_old = Path(self.config.get("REDE", "origem_ag_old"))
            if dir_nuvem.exists() and dir_old.exists():
                for pasta in dir_nuvem.iterdir():
                    if pasta.is_dir():
                        nome_versao = pasta.name
                        exe_old = dir_nuvem / f"FortesAGAtualizador_{nome_versao}.exe"
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
        """Copia um arquivo em blocos (chunks), atualizando a barra de progresso."""
        tamanho_total = origem.stat().st_size
        tamanho_mb = tamanho_total / (1024 * 1024)
        callback_log(f">> Baixando aquivo: {origem.name} ({tamanho_mb:.2f}MB, aguarde...)")

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
        """Executa a rotina completa de download, descompactação e compactação."""
        pasta_destino = self.destino_base / sistema / versao
        pasta_destino.mkdir(parents=True, exist_ok=True)
        arquivos_baixados: list[Path] = []

        # 1. Identificação e Download dos Arquivos conforme as regras de negócio
        if sistema == "AC":
            raiz_ac = Path(self.config.get("REDE", "origem_ac")) / versao
            atualizador_nuvem = raiz_ac / "Nuvem" / "FortesACAtualizadorNuvem.exe"
            ac_nuvem = raiz_ac / "Nuvem" / "AC.exe"
            ac_raiz = raiz_ac / "AC.exe"

            if atualizador_nuvem.exists():
                origem_exe = atualizador_nuvem
            elif ac_nuvem.exists():
                origem_exe = ac_nuvem
                callback_log(">> FortesACAtualizadorNuvem ausente. Usando Nuvem\\AC.exe")
            elif ac_raiz.exists():
                origem_exe = ac_raiz
                callback_log(">> Usando AC.exe da raiz.")
            else:
                raise FileNotFoundError(f"Nenhum executável válido encontrado para AC {versao}")

            dest_exe = pasta_destino / origem_exe.name
            self.copiar_arquivo_com_progresso(origem_exe, dest_exe, callback_progresso, callback_log)
            arquivos_baixados.append(dest_exe)

        elif sistema == "Patrio":
            nome_arquivo = f"FortesPatrioAtualizadorNuvem_{versao}.exe"
            origem = Path(self.config.get("REDE", "origem_patrio")) / versao / "Nuvem" / nome_arquivo
            if not origem.exists():
                raise FileNotFoundError(f"Arquivo {nome_arquivo} não encontrado na rede.")
            dest = pasta_destino / nome_arquivo
            self.copiar_arquivo_com_progresso(origem, dest, callback_progresso, callback_log)
            arquivos_baixados.append(dest)

        elif sistema == "AG":
            origem_ag = Path(self.config.get("REDE", "origem_ag_nuvem")) / versao / "AG.exe"
            if origem_ag.exists():
                dest_ag = pasta_destino / "AG.exe"
                self.copiar_arquivo_com_progresso(origem_ag, dest_ag, callback_progresso, callback_log)
                arquivos_baixados.append(dest_ag)

            nome_old = f"FortesAGAtualizador_{versao}.exe"
            origem_old = Path(self.config.get("REDE", "origem_ag_old")) / nome_old
            if origem_old.exists():
                dest_old = pasta_destino / nome_old
                self.copiar_arquivo_com_progresso(origem_old, dest_old, callback_progresso, callback_log)
                arquivos_baixados.append(dest_old)

        # 2. Descompactação via WinRAR
        if deseja_descompactar:
            callback_log(">> Extração ativada. Invocando WinRAR...")
            for arq in arquivos_baixados:
                self._descompactar_winrar(arq, pasta_destino, callback_log)

        # 3. Compactação em .rar (ou .zip caso WinRAR não exista)
        if deseja_compactar:
            callback_log(">> Compactação ativada. Gerando pacote...")
            self._compactar(sistema, arquivos_baixados, pasta_destino, callback_log)

            # Limpeza dos binários originais soltos, exatamente como no código original
            callback_log(">> Limpeza: removendo executáveis originais soltos...")
            for arq in arquivos_baixados:
                try:
                    arq.unlink(missing_ok=True)
                except Exception as ex:
                    callback_log(f"   [AVISO] Falha ao deletar temporário {arq.name}: {ex}")

        callback_log(">> Processo 100% finalizado!")
        return pasta_destino

    def _descompactar_winrar(self, arquivo: Path, pasta_destino: Path, callback_log: Callable[[str], None]) -> None:
        """Executa a descompactação via WinRAR CLI."""
        if not self.winrar_path.exists():
            return callback_log(f" [ERRO] - Winrar não localizado. Extraçõ ignorada.")

        pasta_extracao = pasta_destino / arquivo.stem
        pasta_extracao.mkdir(exist_ok=True)

        comando = [
            str(self.winrar_path),
            "x",  # Extrair com caminhos completos
            "-ibck",  # Executar em segundo plano
            "-y",  # Sobrescrever automaticamente
            str(arquivo),
            str(pasta_extracao) + "\\"
        ]
        try:
            resultado = subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if resultado.returncode == 0:
                return callback_log(f" -> Extraído com sucesso em: \\{pasta_extracao.name}")
            else:
                return callback_log(f" [AVISO] - Winrar retornou código de aviso/erro: {resultado.returncode}")
        except Exception as e:
            return callback_log(f" [ERRO] - Falha ao executar WinRAR: {e}")

    def _compactar(self,
                   sistema: str,
                   arquivos: list[Path],
                   pasta_destino: Path,
                   callback_log: Callable[[str], None]) -> None:
        """Compacta em .rar caso o WinRAR esteja presente; fallback para .zip caso não esteja."""
        if self.winrar_path.exists():
            rar_destino = pasta_destino / f"Atualiza{sistema}.rar"
            comando = [str(self.winrar_path),
                       "a", # Adiciona ao arquivo
                       "-ep1", # Exclui o diretório base do nome gravado
                       "-y", # Sobrescreve
                       str(rar_destino)
        ] + [str(a) for a in arquivos]

            try:
                subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                return callback_log(f"  ->Arquivo RAR gerado: {rar_destino.name}")
            except Exception as e:
                callback_log(f" [ERRO] - Falha ao criar RAR: {e}. Alternando para ZIP")

        # Fallback nativo: .zip
        zip_detino = pasta_destino / f"Atualiza{sistema}.zip"
        with zipfile.ZipFile(zip_detino, 'w', zipfile.ZipFile) as zipf:
            for arq in arquivos:
                zipf.write(arq, arcname=arq.name)
        callback_log(f" -> Arquivo ZIP gerado: {zip_detino.name}")

    @staticmethod
    def _formatar_data(timestamp: float) -> str:
        """Converte timestamp POSIX para formato legível no Brasil."""
        dt = datetime.datetime.fromtimestamp(timestamp)
        return  dt.strftime("%d/%m/%Y %H:%M:%S")