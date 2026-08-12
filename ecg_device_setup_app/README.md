# ECG Device Setup App

Aplicação desktop local para conduzir, com segurança e rastreabilidade, a preparação de um kit composto por um celular Android, um relógio, um participante, um kit e uma nova conta Google.

## Estado atual

O projeto possui agora um **wizard PySide6 funcional de pré-validação**.

Já está implementado:

- tela para participante, kit, e-mail e senha Google;
- senha mantida somente em memória, mascarada e excluída de serializações;
- detecção assíncrona do celular por ADB, sem travar a interface;
- apresentação de modelo, fabricante, serial, Android, build e transporte;
- mensagens específicas para dispositivo não autorizado, offline ou ausente;
- pré-validação assíncrona de configurações, APKs, pastas, espaço livre, ADB e celular;
- resumo final com e-mail mascarado e confirmação obrigatória do operador;
- painel recolhível de logs operacionais seguros;
- modo CLI de preflight preservado;
- testes de backend e testes de interface com `pytest-qt`.

Ainda não estão implementados:

- backup dos arquivos do celular;
- remoção da conta Samsung;
- limpeza de `Documents` e `Downloads`;
- instalação dos APKs;
- configuração interna dos aplicativos;
- pareamento e configuração do relógio;
- persistência e retomada completa do workflow.

O botão final do wizard **não executa ações destrutivas**. Ele apenas confirma que o ambiente passou pela pré-validação.

## Requisitos

- Windows 10 ou 11;
- Python 3.11 ou superior;
- Android SDK Platform Tools, com `adb.exe` no `PATH`, ou caminho configurado em `config/settings.yaml`;
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

Confirme o ADB:

```powershell
adb version
adb devices -l
```

Caso o `adb.exe` não esteja no `PATH`, configure o caminho em `config/settings.yaml`:

```yaml
adb:
  executable: C:\Android\platform-tools\adb.exe
```

## Abrir a interface

```powershell
python .\main.py
```

Fluxo atual:

1. informar participante, kit, conta e senha Google;
2. detectar o celular conectado;
3. executar a pré-validação;
4. revisar e confirmar os dados.

As consultas ADB e o preflight rodam fora da thread principal da interface.

## Executar somente o preflight no terminal

```powershell
python .\main.py --preflight `
  --participant-id ABC-12-2345 `
  --kit-id 12 `
  --google-email conta@gmail.com
```

A senha é solicitada com entrada protegida.

## APKs esperados

```text
apks/phone/GPT_HRPClinical_Release_2_0_6_Phone.apk
apks/phone/com_sec_smartring2-Phone-24120318-1_3_4-1.apk
apks/watch/GPT_HRPClinical_2_2_2_Watch.apk
apks/watch/GPT_MultiFreqBia_v1_3_1.apk
apks/watch/GPT_com.sec.cola_release_1.0.85.apk
```

O catálogo está em `config/applications.yaml`.

## Estrutura

```text
backend/adb/                 cliente ADB e detecção de dispositivos
backend/models/              modelos de domínio e entrada segura
backend/services/            configurações, APKs e preflight
backend/workflows/           reservado para o workflow operacional
frontend/app.py              inicialização do PySide6
frontend/main_window.py      janela e navegação do wizard
frontend/controllers/        estado e integração com o backend
frontend/steps/              páginas do wizard
frontend/widgets/            componentes visuais reutilizáveis
frontend/workers.py          execução assíncrona
config/                      arquivos YAML
data/                        logs, sessões, relatórios e backups
apks/                        instaladores locais
tests/                       testes de backend e interface
```

## Segurança

- comandos ADB usam listas de argumentos e `shell=False`;
- a senha Google não integra modelos persistentes;
- a senha não aparece no resumo, nos logs ou no `model_dump`;
- o e-mail é parcialmente mascarado na confirmação;
- tarefas demoradas não bloqueiam a janela;
- nenhum comando de limpeza, reset ou instalação é chamado pelo frontend atual;
- erros conhecidos são apresentados ao operador sem depender de traceback.

## Testes

```powershell
python -m pytest -q
```

Os testes de interface usam `pytest-qt` e não dependem de celular físico.
