"""
app.py
Interface Gráfica em Tkinter/TTK com visual escuro Catppuccin Macchiato.
Construção modular em Grid com tratamento de redimensionamento proporcional.
"""

from __future__ import annotations
import ctypes
import os
from pathlib import Path
import sys  # Módulo adicionado para resolver o NameError
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from service import UpdaterService


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        # Força o Windows a reconhecer a aplicação como entidade individual na barra de tarefas
        try:
            app_id = "fortes.updaterfinder.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

        self.title("Buscador de Atualizadores Fortes")
        self.geometry("820x720")
        self.minsize(720, 600)

        # Resolução segura do ícone tanto no ambiente de desenvolvimento quanto compilado
        caminho_icone = self._obter_caminho_recurso("buscador.ico")
        if os.path.exists(caminho_icone):
            self.iconbitmap(caminho_icone)

        self.service = UpdaterService()
        self._configurar_tema()
        self._construir_interface()

    @staticmethod
    def _obter_caminho_recurso(nome_arquivo: str) -> str:
        """Resolve o caminho absoluto tanto em desenvolvimento quanto no bundle PyInstaller."""
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, nome_arquivo)
        return os.path.join(os.path.abspath("."), nome_arquivo)

    def _configurar_tema(self) -> None:
        """Configura a paleta escura utilizando as propriedades completas do TTK."""
        self.bg_color = "#1e1e2e"       # Fundo base
        self.fg_color = "#cdd6f4"       # Texto claro
        self.card_bg = "#313244"        # Fundo de tabelas e containers
        self.accent_color = "#89b4fa"   # Azul de destaque
        self.console_bg = "#11111b"     # Fundo preto para logs
        self.console_fg = "#a6e3a1"     # Verde terminal

        self.configure(bg=self.bg_color)
        estilo = ttk.Style(self)
        estilo.theme_use("clam")

        estilo.configure(
            ".",
            background=self.bg_color,
            foreground=self.fg_color,
            font=("Segoe UI", 10)
        )
        estilo.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        estilo.configure("TCheckbutton", background=self.bg_color, foreground=self.fg_color)
        estilo.configure(
            "TCombobox",
            fieldbackground=self.card_bg,
            background=self.card_bg,
            foreground=self.fg_color
        )

        # Botão estilizado com estados dinâmicos
        estilo.configure(
            "Accent.TButton",
            background=self.accent_color,
            foreground="#11111b",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0
        )
        estilo.map("Accent.TButton", background=[("active", "#b4befe"), ("disabled", "#45475a")])

        # Tabela (Treeview)
        estilo.configure(
            "Treeview",
            background=self.card_bg,
            foreground=self.fg_color,
            fieldbackground=self.card_bg,
            rowheight=26,
            borderwidth=0
        )
        estilo.configure(
            "Treeview.Heading",
            background="#45475a",
            foreground=self.fg_color,
            font=("Segoe UI", 10, "bold")
        )
        estilo.map("Treeview", background=[("selected", self.accent_color)], foreground=[("selected", "#11111b")])

        # Barra de Progresso
        estilo.configure("Horizontal.TProgressbar", troughcolor=self.card_bg, background="#a6e3a1", borderwidth=0)

    def _construir_interface(self) -> None:
        """Monta a hierarquia visual responsiva em Grid."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        container = tk.Frame(self, bg=self.bg_color)
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
        container.grid_columnconfigure(0, weight=1)

        # ==================== LINHA 0 & 1: CABEÇALHO ====================
        lbl_titulo = tk.Label(
            container,
            text="Buscador de Atualizadores Fortes",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_color,
            fg=self.accent_color
        )
        lbl_titulo.grid(row=0, column=0, sticky="w")

        lbl_assinatura = tk.Label(
            container,
            text="Desenvolvido por Gabriel Levi",
            font=("Segoe UI", 9, "italic"),
            bg=self.bg_color,
            fg="#a6adc8"
        )
        lbl_assinatura.grid(row=1, column=0, pady=(2, 15), sticky="w")

        # ==================== LINHA 2: FILTRO ====================
        frame_filtro = tk.Frame(container, bg=self.bg_color)
        frame_filtro.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        lbl_combo = tk.Label(frame_filtro, text="Selecione um sistema:", font=("Segoe UI", 10, "bold"))
        lbl_combo.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.combo_sistema = ttk.Combobox(frame_filtro, values=["AC", "AG", "Patrio"], state="readonly", width=15)
        self.combo_sistema.grid(row=0, column=1, padx=(0, 10), sticky="w")
        self.combo_sistema.bind("<<ComboboxSelected>>", self._ao_selecionar_sistema)

        self.lbl_status_busca = tk.Label(frame_filtro, text="", fg=self.accent_color)
        self.lbl_status_busca.grid(row=0, column=2, sticky="w")

        # ==================== LINHA 3: TABELA DE VERSÕES ====================
        frame_tabela = tk.Frame(container, bg=self.bg_color)
        frame_tabela.grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        frame_tabela.grid_rowconfigure(0, weight=1)
        frame_tabela.grid_columnconfigure(0, weight=1)

        colunas = ("versao", "data")
        self.tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=6)
        self.tabela.heading("versao", text="Versão Encontrada")
        self.tabela.heading("data", text="Data da Última Modificação")

        self.tabela.column("versao", width=220, anchor="w")
        self.tabela.column("data", width=250, anchor="center")

        scroll_tabela = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll_tabela.set)

        self.tabela.grid(row=0, column=0, sticky="nsew")
        scroll_tabela.grid(row=0, column=1, sticky="ns")

        self.tabela.bind("<<TreeviewSelect>>", lambda e: self._validar_selecao_tabela())

        # ==================== LINHA 4: AÇÕES ====================
        frame_acoes = tk.Frame(container, bg=self.bg_color)
        frame_acoes.grid(row=4, column=0, sticky="ew", pady=(0, 15))
        frame_acoes.grid_columnconfigure(2, weight=1)

        self.var_descompactar = tk.BooleanVar(value=False)
        self.chk_descompactar = ttk.Checkbutton(
            frame_acoes, text="Descompactar após baixar", variable=self.var_descompactar
        )
        self.chk_descompactar.grid(row=0, column=0, padx=(0, 15), sticky="w")

        self.var_compactar = tk.BooleanVar(value=False)
        self.chk_compactar = ttk.Checkbutton(
            frame_acoes, text="Compactar em .rar/.zip após baixar", variable=self.var_compactar
        )
        self.chk_compactar.grid(row=0, column=1, sticky="w")

        self.btn_executar = ttk.Button(
            frame_acoes,
            text="Executar Download",
            style="Accent.TButton",
            command=self._iniciar_fluxo_copia,
            state="disabled"
        )
        self.btn_executar.grid(row=0, column=2, sticky="e", ipadx=10, ipady=3)

        # ==================== LINHA 5: BARRA DE PROGRESSO ====================
        self.progresso = ttk.Progressbar(container, orient="horizontal", mode="determinate")
        self.progresso.grid(row=5, column=0, sticky="ew", pady=(0, 10))

        # ==================== LINHA 6: CONSOLE DE LOGS ====================
        self.txt_log = ScrolledText(
            container,
            bg=self.console_bg,
            fg=self.console_fg,
            insertbackground="white",
            font=("Consolas", 9),
            height=8,
            relief="flat"
        )
        self.txt_log.grid(row=6, column=0, sticky="nsew")

        container.grid_rowconfigure(3, weight=2)
        container.grid_rowconfigure(6, weight=1)

        self._escrever_log("[SISTEMA] Selecione um sistema para listar as versões disponíveis.")

    # --- Métodos de Interação da UI ---

    def _escrever_log(self, mensagem: str) -> None:
        """Insere mensagens no console de logs com rolagem automática."""
        self.txt_log.insert(tk.END, mensagem + "\n")
        self.txt_log.see(tk.END)

    def _atualizar_progresso(self, valor: float) -> None:
        """Atualiza a barra de progresso (0 a 100)."""
        self.progresso["value"] = valor

    def _validar_selecao_tabela(self) -> None:
        """Habilita o botão apenas quando houver seleção válida."""
        selecionado = self.tabela.selection()
        if selecionado:
            self.btn_executar.config(state="normal")
        else:
            self.btn_executar.config(state="disabled")

    def _ao_selecionar_sistema(self, event=None) -> None:
        """Dispara busca assíncrona para manter a janela responsiva."""
        sistema = self.combo_sistema.get()
        if not sistema:
            return

        self.lbl_status_busca.config(text=f"Realizando varredura em {sistema}, aguarde...")
        self.btn_executar.config(state="disabled")

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        threading.Thread(target=self._buscar_versoes_worker, args=(sistema,), daemon=True).start()

    def _buscar_versoes_worker(self, sistema: str) -> None:
        """Executa a listagem no backend de arquivos."""
        try:
            versoes = self.service.listar_versoes(sistema)
            self.after(0, self._popular_tabela, versoes)
        except Exception as e:
            self.after(0, self._escrever_log, f"[ERRO] Falha ao listar {sistema}: {e}")
            self.after(0, self.lbl_status_busca.config, {"text": "Erro de conexão"})

    def _popular_tabela(self, versoes: list[dict[str, str]]) -> None:
        """Preenche o TreeView com as versões localizadas."""
        for item in versoes:
            self.tabela.insert("", tk.END, values=(item["versao"], item["data"]))

        total = len(versoes)
        self.lbl_status_busca.config(text=f"{total} versões encontradas")
        self._escrever_log(f">> Carregamento concluído: {total} versão(ões) disponível(is).")

    def _iniciar_fluxo_copia(self) -> None:
        """Valida e inicializa o processo de cópia."""
        selecionado = self.tabela.selection()
        if not selecionado:
            return

        # Leitura imutável da string para evitar conversões indesejadas
        versao = str(self.tabela.set(selecionado[0], "versao"))
        sistema = self.combo_sistema.get()

        resposta = messagebox.askyesno(
            "Confirmar Download",
            f"Deseja baixar e processar os arquivos do sistema {sistema}?\nVersão: {versao}"
        )
        if not resposta:
            return

        self.btn_executar.config(state="disabled")
        self.combo_sistema.config(state="disabled")
        self.progresso["value"] = 0

        deseja_descomp = self.var_descompactar.get()
        deseja_comp = self.var_compactar.get()

        threading.Thread(
            target=self._executar_copia_worker,
            args=(sistema, versao, deseja_descomp, deseja_comp),
            daemon=True
        ).start()

    def _executar_copia_worker(self, sistema: str, versao: str, descomp: bool, comp: bool) -> None:
        """Worker desacoplado da interface visual."""
        try:
            pasta_final = self.service.processar_download(
                sistema=sistema,
                versao=versao,
                deseja_descompactar=descomp,
                deseja_compactar=comp,
                callback_progresso=lambda p: self.after(0, self._atualizar_progresso, p),
                callback_log=lambda msg: self.after(0, self._escrever_log, msg)
            )
            self.after(0, self._concluir_sucesso, pasta_final)
        except Exception as e:
            self.after(0, self._tratar_erro_copia, str(e))

    def _concluir_sucesso(self, pasta_destino: Path) -> None:
        """Finalização de tarefa com feedback de abertura de diretório."""
        self.progresso["value"] = 100
        self.btn_executar.config(state="normal")
        self.combo_sistema.config(state="readonly")

        abrir = messagebox.askyesno(
            "Sucesso!",
            "Arquivos baixados e processados com sucesso!\n\nDeseja abrir a pasta de destino?"
        )
        if abrir and pasta_destino.exists():
            os.startfile(str(pasta_destino))

    def _tratar_erro_copia(self, erro_msg: str) -> None:
        """Restaura o estado dos controles em caso de falha."""
        self.progresso["value"] = 0
        self.btn_executar.config(state="normal")
        self.combo_sistema.config(state="readonly")
        self._escrever_log(f"\n[ERRO CRÍTICO] -> {erro_msg}")
        messagebox.showerror(
            "Erro no Processamento",
            f"Ocorreu um erro durante a operação:\n\n{erro_msg}"
        )


if __name__ == "__main__":
    app = App()
    app.mainloop()