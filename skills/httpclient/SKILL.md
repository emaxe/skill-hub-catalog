---
name: httpclient
description: "Правила работы с HTTP клиентом в .NET. Используй когда пользователь создает HTTP клиенты, настраивает прокси, таймауты, или интегрируется с внешними API через HttpClient/IHttpClientFactory."
tags: [architecture, dotnet]
author: maksimklisin
version: "1.0.0"
scope: global
platforms: [claude-code, cursor, copilot]
dependencies: []
language: csharp
---

# Правила работы с HTTP клиентом

## Создание HttpClient

1. **IHttpClientFactory**: HTTP клиент всегда должен создаваться только через `IHttpClientFactory.CreateClient()`
   - Никогда не создавай `HttpClient` напрямую через `new HttpClient()`
   - Инжектируй `IHttpClientFactory` в конструктор сервиса через DI
   - Используй `httpClientFactory.CreateClient()` для получения экземпляра клиента

2. **Пример использования**:
   ```csharp
   public class MyService
   {
       private readonly HttpClient _httpClient;
       
       public MyService(IHttpClientFactory httpClientFactory)
       {
           _httpClient = httpClientFactory.CreateClient();
       }
   }
   ```

## Таймауты

1. **Дефолтный таймаут**: дефолтный таймаут для HTTP клиента составляет 30 секунд
   - Если требуется другой таймаут, явно устанавливай его через `_httpClient.Timeout = TimeSpan.FromSeconds(30)`
   - Для именованных клиентов настраивай таймаут при регистрации в DI контейнере

2. **Настройка именованных клиентов**:
   ```csharp
   services.AddHttpClient("MyClient")
       .ConfigureHttpClient(client => 
       {
           client.Timeout = TimeSpan.FromSeconds(30);
       });
   ```

## Прокси

1. **Настройка прокси**: для настройки прокси используй `ConfigurePrimaryHttpMessageHandler` при регистрации HTTP клиента

2. **Пример настройки прокси**:
   ```csharp
   services.AddHttpClient("MyClient")
       .ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler
       {
           Proxy = new WebProxy("http://proxy.example.com:8080")
           {
               Credentials = new NetworkCredential("username", "password")
           },
           UseProxy = true
       })
       .ConfigureHttpClient(client => 
       {
           client.Timeout = TimeSpan.FromSeconds(30);
       });
   ```

3. **Прокси без аутентификации**:
   ```csharp
   services.AddHttpClient("MyClient")
       .ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler
       {
           Proxy = new WebProxy("http://proxy.example.com:8080"),
           UseProxy = true
       });
   ```

4. **Отключение прокси**:
   ```csharp
   services.AddHttpClient("MyClient")
       .ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler
       {
           UseProxy = false
       });
   ```

## Best Practices

1. **Dispose**: не вызывай `Dispose()` на клиенте, созданном через `IHttpClientFactory` — фабрика управляет жизненным циклом
