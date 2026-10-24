# ExeSniffer — Buscador de Atualizadores Fortes

Aplicação desktop desenvolvida em **Python + Tkinter/TTK** para localizar versões de atualizadores dos sistemas Fortes em diretórios de rede e facilitar a cópia, extração e compactação dos pacotes.

O projeto foi criado para apoiar rotinas operacionais de infraestrutura e atualização de aplicações, reunindo em uma interface gráfica a consulta de versões, o processamento dos arquivos e o acompanhamento por logs e barra de progresso.

> **Atenção:** o programa foi desenvolvido para um ambiente específico. Para utilizá-lo em outra rede, ajuste os caminhos no `config.ini` e valide o processo com arquivos de teste antes de utilizá-lo em produção.

## Funcionalidades

- Consulta de versões disponíveis dos sistemas **AC**, **AG** e **Patrio**.
- Exibição da versão e da data de modificação encontrada no diretório de origem.
- Cópia dos executáveis da rede para uma pasta local.
- Barra de progresso e console de logs durante o processamento.
- Opção para extrair o conteúdo dos executáveis usando o WinRAR.
- Opção para compactar o resultado em arquivo `.rar`, com alternativa em `.zip` caso a compactação RAR não seja concluída.
- Configuração dos caminhos de origem, diretório de destino e caminho do WinRAR por meio de `config.ini`.
- Interface escura construída com Tkinter e widgets TTK.

## Tecnologias utilizadas

- **Python 3.10 ou superior**
- **Tkinter / ttk** — interface gráfica
- **pathlib, shutil, zipfile, configparser e subprocess** — manipulação de arquivos, configuração e execução de ferramentas externas
- **WinRAR** — extração dos pacotes e tentativa de compactação em RAR

A interface gráfica e as operações principais utilizam módulos da biblioteca padrão do Python. O WinRAR é um requisito externo para as funções de extração e compactação RAR.

## Estrutura do repositório

```text
Exesniffer/
├── app.py          # Interface gráfica e eventos da aplicação
├── service.py      # Regras de negócio para localizar e processar atualizadores
├── config.ini      # Caminhos de rede, destino local e caminho do WinRAR
├── buscador.ico    # Ícone da aplicação
└── README.md       # Documentação do projeto
```

### Responsabilidade de cada arquivo

- **`app.py`**: cria a janela, apresenta as versões disponíveis, recebe as opções do usuário e exibe o progresso e os logs.
- **`service.py`**: consulta os diretórios configurados, localiza os arquivos, copia os executáveis e coordena a extração, compactação e limpeza dos arquivos temporários.
- **`config.ini`**: armazena os caminhos específicos do ambiente. Ajuste esses valores antes de executar o projeto.
- **`buscador.ico`**: ícone utilizado na janela.

## Requisitos

Antes de executar, verifique:

1. Windows com Python instalado.
2. Acesso aos compartilhamentos de rede configurados.
3. Permissão de leitura nas pastas de origem e de escrita no destino.
4. WinRAR instalado e acessível no caminho definido em `config.ini`, caso utilize extração ou compactação.
5. Os arquivos e diretórios correspondentes às versões que deseja processar realmente existirem na rede.

## Instalação e execução

### 1. Clonar o repositório

```powershell
git clone https://github.com/Biellima2811/Exesniffer.git
cd Exesniffer
```

### 2. Conferir a versão do Python

```powershell
py --version
```

O projeto utiliza recursos de tipagem disponíveis nas versões modernas do Python. Recomenda-se Python 3.10 ou superior.

### 3. Configurar o `config.ini`

Abra o arquivo `config.ini` e configure os caminhos de acordo com o seu ambiente.

Exemplo ilustrativo — substitua os caminhos de exemplo pelos caminhos autorizados da sua rede:

```ini
[CONFIGURACOES]
destino_base =
winrar_path = C:\Program Files\WinRAR\WinRAR.exe

[REDE]
origem_ac = \\SERVIDOR\COMPARTILHAMENTO\AC\Portal
origem_ag_nuvem = \\SERVIDOR\COMPARTILHAMENTO\AG\Deploy\nuvem
origem_ag_old = \\SERVIDOR\COMPARTILHAMENTO\AG\Deploy\old
origem_patrio = \\SERVIDOR\COMPARTILHAMENTO\Patrio\Portal
```

- `destino_base`: diretório local em que os arquivos processados serão salvos. Se ficar vazio, o programa utiliza `Documentos/Atualiza_Nuvem` dentro do perfil do usuário.
- `winrar_path`: caminho completo do executável do WinRAR.
- `origem_ac`, `origem_ag_nuvem`, `origem_ag_old` e `origem_patrio`: diretórios de origem consultados para localizar versões e arquivos.

**Importante:** mantenha os caminhos de rede reais apenas na configuração local do ambiente. Não publique endereços internos, credenciais ou outros dados operacionais que não devam ser públicos.

### 4. Iniciar a aplicação

Na pasta do projeto, execute:

```powershell
py app.py
```

A janela do Buscador de Atualizadores Fortes deverá ser aberta.

## Como utilizar

1. Abra a aplicação.
2. Selecione o sistema desejado: `AC`, `AG` ou `Patrio`.
3. Aguarde a consulta das versões disponíveis.
4. Selecione a versão que deseja processar.
5. Marque, conforme a necessidade, as opções de descompactação e/ou compactação.
6. Clique em **Executar Download**.
7. Acompanhe a barra de progresso e as mensagens exibidas no console de logs.

Os arquivos processados são organizados no diretório de destino configurado, em subpastas por sistema e versão.

> Execute o processo primeiro em uma pasta de teste e confirme se o conteúdo gerado está correto antes de utilizá-lo em uma rotina operacional.

## Solução de problemas

### Nenhuma versão é exibida

- Verifique se os caminhos no `config.ini` estão corretos.
- Confirme se o usuário possui acesso aos compartilhamentos de rede.
- Teste se as pastas de origem estão acessíveis pelo Explorador de Arquivos do Windows.

### Arquivo não encontrado

- Confirme se a versão selecionada existe no diretório correspondente.
- Verifique se os nomes e a estrutura das pastas correspondem ao esperado pelo programa.
- Consulte as mensagens no console de logs.

### WinRAR não encontrado

- Confirme se o WinRAR está instalado.
- Atualize `winrar_path` no `config.ini` para apontar para o executável correto.
- Se a compactação RAR falhar, o serviço tenta gerar um pacote ZIP alternativo.

### Erro de permissão ou gravação

- Confirme se o usuário possui permissão de leitura na origem e de gravação no destino.
- Evite executar o programa com privilégios elevados sem necessidade.
- Não teste a ferramenta diretamente em diretórios críticos sem autorização e backup.

## Segurança e uso responsável

- Utilize a ferramenta apenas em redes, diretórios e arquivos para os quais você tenha autorização.
- Verifique o conteúdo dos pacotes antes de distribuí-los ou utilizá-los.
- Não publique configurações internas do ambiente em repositórios públicos.
- Teste alterações em um ambiente controlado antes de utilizá-las em produção.

## Objetivo de aprendizado

Este projeto também serve como exercício prático de Python, incluindo:

- Programação orientada a objetos.
- Interface gráfica com Tkinter/TTK.
- Separação entre interface e regras de negócio.
- Leitura de arquivos INI.
- Manipulação de caminhos e arquivos.
- Execução de processos externos.
- Callbacks, logs e atualização de progresso.

## Autor

Desenvolvido por **Biellima2811**.

Repositório: [github.com/Biellima2811/Exesniffer](https://github.com/Biellima2811/Exesniffer)
