# ECG Device Setup App

Aplicação desktop local para conduzir, com segurança e rastreabilidade, a
preparação de um kit composto por um Samsung Galaxy A56, um Galaxy Watch 8,
um participante, um kit e uma nova conta Google.

## Estado atual

A **Etapa 1** está implementada:

- projeto independente e backend desacoplado de interface;
- modelos de entrada, dispositivo, sessão, aplicativo e resultado;
- senha Google apenas em memória, mascarada e excluída de serializações;
- cliente ADB central, sem `shell=True`, com timeout, dispositivo explícito,
  entrada padrão segura e cancelamento cooperativo;
- parser de `adb devices -l` e detecção do único celular USB autorizado;
- leitura das propriedades mínimas do aparelho;
- alerta não bloqueante quando o modelo não parece ser Galaxy A56;
- catálogo YAML dos cinco APKs;
- preflight agregado de ADB, APKs, celular, espaço livre e escrita local;
- filtro de logs para senha, pairing code, tokens e segredos cadastrados;
- testes unitários sem dispositivo real.

Ainda não estão implementados: backup e limpeza (Etapa 2), máquina de estados e
instalação/pareamento (Etapa 3), wizard PySide6 (Etapa 4), validação final e
relatórios (Etapa 5). Nenhuma ação destrutiva é executada nesta etapa.

## Requisitos

- Windows 10 ou 11;
- Python 3.11 ou superior;
- Android SDK Platform Tools, com `adb.exe` no `PATH`, ou caminho configurado em
  `config/settings.yaml`;
- cabo USB de dados;
- depuração USB habilitada e autorizada no celular.

## Instalação

No PowerShell, a partir desta pasta:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Baixe o Android SDK Platform Tools no site oficial do Android, extraia o pacote
e adicione a pasta que contém `adb.exe` ao `PATH`. Alternativamente, informe o
caminho absoluto:

```yaml
adb:
  executable: C:\Android\platform-tools\adb.exe
```

Confirme a instalação com:

```powershell
adb version
adb devices -l
```

## APKs

Copie os arquivos para os destinos abaixo:

```text
apks/phone/GPT_HRPClinical_Release_2_0_6_Phone.apk
apks/phone/com_sec_smartring2-Phone-24120318-1_3_4-1.apk
apks/watch/GPT_HRPClinical_2_2_2_Watch.apk
apks/watch/GPT_MultiFreqBia_v1_3_1.apk
apks/watch/GPT_com.sec.cola_release_1.0.85.apk
```

O catálogo está em `config/applications.yaml`. Para adicionar um APK, inclua
uma entrada no grupo `phone` ou `watch` e coloque o arquivo somente na pasta
correspondente. Nomes que tentem sair dessa pasta são rejeitados.

## Diagnóstico da Etapa 1

O ponto de entrada atual é um preflight não destrutivo:

```powershell
python main.py --preflight `
  --participant-id EDI-21-2196 `
  --kit-id KIT-03 `
  --google-email ecg_p21@uea.edu.br
```

A senha é solicitada com entrada protegida, permanece apenas em memória e não
aparece no resumo. O preflight pode terminar com alertas e ainda estar pronto;
falhas impedem o provisionamento. A confirmação formal do operador será feita
no wizard da Etapa 4.

## Estrutura

```text
backend/adb/       cliente ADB, resultado de comando e detecção
backend/models/    modelos sem dependência de PySide6
backend/services/  configuração, catálogo de APKs e preflight
backend/workflows/ reservado para a máquina de estados da Etapa 3
config/            configurações fixas em YAML
apks/              binários locais ignorados pelo Git
data/              backups, sessões, relatórios e logs ignorados pelo Git
frontend/          reservado para o wizard PySide6 da Etapa 4
tests/             testes unitários com ADB simulado
```

## Segurança

- o cliente usa listas de argumentos e `shell=False`;
- a senha Google não integra modelos persistentes;
- códigos de pareamento serão enviados por `stdin`, nunca por argumento ou log;
- nenhum comando destrutivo existe na Etapa 1;
- os APKs são resolvidos com `pathlib` e confinados à pasta do dispositivo;
- o preflight é somente diagnóstico;
- dados clínicos não são lidos nem registrados.

## Testes

```powershell
python -m pytest -q
```

Os testes usam processos e respostas ADB simulados; não conecte um dispositivo
para executá-los.

## Próximas etapas

A persistência atômica e a retomada entram na Etapa 2. A máquina de estados
impedirá limpeza e reset antes do backup validado na Etapa 3. O frontend da
Etapa 4 chamará somente serviços do backend e executará tarefas longas fora da
thread da interface.
