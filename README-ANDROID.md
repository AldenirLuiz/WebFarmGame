# Fazenda Paraíso para Android

O app usa Capacitor para abrir a versão local do jogo em uma WebView. A interface,
PyScript/Pyodide e os arquivos do jogo ficam dentro do APK; não é necessário
hospedar o jogo nem ter conexão com a internet para executá-lo.

## Requisitos

- Node.js 20 ou superior (recomendado: versão LTS).
- Android Studio com Android SDK instalado e uma plataforma Android selecionada.
- JDK 21, normalmente disponível pelo Android Studio (jbr).

## Gerar o APK de teste

No PowerShell, na pasta do projeto:

```powershell
npm install
npm run build:web
npm run android:init
npm run android:debug
```

O primeiro build precisa baixar as dependências do Capacitor e do Gradle. Se o
Android SDK estiver fora do caminho padrão, configure `ANDROID_HOME` ou
`ANDROID_SDK_ROOT` antes de executar os comandos.

O APK de depuração será gerado em:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

Para instalar em um celular conectado com depuração USB habilitada:

```powershell
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

Depois de alterar os arquivos do jogo, execute `npm run android:debug` de novo
para reconstruir os assets e o APK.

## Observações

- `npm run build:web` copia `teste.html` como `www/index.html`, os módulos
  Python, `insumos.json`, o CSS e os arquivos locais do PyScript. Arquivos
  `.map` de depuração são omitidos para reduzir o tamanho do pacote.
- O jogo mantém o progresso no `localStorage` da WebView. Evite limpar os dados
  do aplicativo se quiser preservar o save local.
- O APK de depuração serve para testes. Para distribuir o jogo, será necessário
  configurar uma chave de assinatura e gerar uma versão release.
