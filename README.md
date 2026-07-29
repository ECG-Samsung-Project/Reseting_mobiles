# Reseting_mobiles

## Envio ao servidor

A aba **Enviar ao servidor** compara e envia arquivos destas pastas em
`landing/raw`:

- `mobile_fl_data`
- `mobile_ic_data`
- `watch_fl_data`
- `watch_ic_data`
- `ecg_data`
- `holter_data`
- `looper_data`
- `eco_data`
- `redcap_data`
- `blood_test_data`
- `bio_data`

### Configuração

1. Instale as dependências:

   ```powershell
   pip install -r requirements.txt
   ```

2. Copie `.env.example` para `.env` e preencha os dados reais do servidor.

3. Cadastre e confira previamente a chave pública do servidor no arquivo
   `known_hosts`. Conexões com identidade SSH desconhecida são rejeitadas.

O arquivo `.env` é ignorado pelo Git. Não coloque senhas, chaves privadas ou
credenciais no `.env.example`.

Para autenticação por senha, use:

```dotenv
ECG_SYNC_AUTH_METHOD=password
ECG_SYNC_PASSWORD=
```

Com a senha vazia, a interface abre uma janela mascarada ao verificar o
servidor. A senha permanece somente na memória durante a comparação e o upload.

### Segurança do upload

Somente arquivos classificados como novos podem ser selecionados. Cada envio
usa um nome temporário terminado em `.part`, valida o tamanho e tenta validar
SHA-256 antes da renomeação definitiva. Conflitos não são sobrescritos e nenhum
arquivo local ou remoto é apagado automaticamente.

### Testes

Com `extração` no `PYTHONPATH`:

```powershell
$env:PYTHONPATH = (Resolve-Path "extração").Path
python -m unittest discover -s "tests\server_sync" -v
```
