# Reseting_mobiles

Ferramentas de preparação dos dispositivos e criação de lotes do projeto ECG.

- `apps/`: APKs utilizados na instalação.
- `instalação/`: interface de instalação, configuração e reset dos dispositivos.
- `batch_maker/`: criação de lotes e download de arquivos de participantes.
- `other_files/`: arquivos de apoio à configuração.

## Dependências e execução

Requer Python 3.11 ou superior, Tkinter e Android Platform Tools (`adb` no PATH).
Na raiz do projeto:

```powershell
pip install -r requirements.txt
python instalação/main.py
```

Para criar lotes, execute `python batch_maker/main.py`.
`customtkinter` é usado na instalação e `paramiko` no download do batch_maker.

## Extração e sincronização

A aplicação de extração foi movida para o projeto irmão
[ecg-extraction](https://github.com/ECG-Samsung-Project/ecg-extraction).
As cinco abas, `.env.example`, dependências e testes de `server_sync` ficam
nesse repositório. Execute `python main.py` na raiz de ecg-extraction e mantenha
ali seu próprio `.env`; a configuração local antiga não é migrada automaticamente.
Dados, APKs, credenciais e arquivos de saída não fazem parte da migração.

## Credencial SSH pendente

`batch_maker/download_participant.py` contém uma credencial SSH hardcoded.
Ela precisa ser revogada e substituída por variável de ambiente.
Não reutilize essa credencial no novo projeto.
