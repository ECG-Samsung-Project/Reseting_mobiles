"""Exceções de domínio convertíveis em mensagens amigáveis no frontend."""


class EcgDeviceSetupError(Exception):
    """Erro base conhecido pela aplicação."""


class AdbNotFoundError(EcgDeviceSetupError):
    """O executável ADB não foi encontrado."""


class AdbCommandError(EcgDeviceSetupError):
    """Um comando ADB terminou com erro."""


class AdbTimeoutError(AdbCommandError):
    """Um comando ADB ultrapassou o tempo limite."""


class AdbCancelledError(AdbCommandError):
    """Um comando ADB foi cancelado."""


class DeviceNotFoundError(EcgDeviceSetupError):
    """Nenhum dispositivo adequado foi encontrado."""


class DeviceUnauthorizedError(EcgDeviceSetupError):
    """O dispositivo ainda não autorizou a depuração USB."""


class MultipleDevicesError(EcgDeviceSetupError):
    """Mais de um dispositivo elegível foi encontrado."""


class BackupError(EcgDeviceSetupError):
    """Falha ao criar o backup."""


class BackupValidationError(BackupError):
    """O backup criado não passou na validação."""


class UnsafeDeletePathError(EcgDeviceSetupError):
    """Uma remoção fora dos caminhos permitidos foi bloqueada."""


class ApkNotFoundError(EcgDeviceSetupError):
    """Um APK obrigatório não foi encontrado."""


class ApkInstallError(EcgDeviceSetupError):
    """Falha ao instalar um APK."""


class WatchPairingError(EcgDeviceSetupError):
    """Falha ao parear ou conectar o relógio."""


class InvalidWorkflowTransitionError(EcgDeviceSetupError):
    """A transição solicitada não é válida no estado atual."""


class SessionPersistenceError(EcgDeviceSetupError):
    """Falha ao salvar ou recuperar uma sessão."""


class ConfigurationError(EcgDeviceSetupError):
    """A configuração YAML é inválida ou insegura."""
