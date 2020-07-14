---
date: 2020-6-16
layout: default
title: spring配置管理

---

# spring配置管理

![image-20200616103950075](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200616103950075.png)

## 继承体系

![image-20200616161314523](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200616161314523.png)

![image-20200616135125293](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200616135125293.png)



org.springframework.boot.SpringApplication#run(java.lang.String...)

​	org.springframework.boot.SpringApplication#prepareEnvironment

```java
private ConfigurableEnvironment prepareEnvironment(SpringApplicationRunListeners listeners,
      ApplicationArguments applicationArguments) {
   // Create and configure the environment
   ConfigurableEnvironment environment = getOrCreateEnvironment();
   configureEnvironment(environment, applicationArguments.getSourceArgs());
   ConfigurationPropertySources.attach(environment);
   listeners.environmentPrepared(environment);
   bindToSpringApplication(environment);
   if (!this.isCustomEnvironment) {
      environment = new EnvironmentConverter(getClassLoader()).convertEnvironmentIfNecessary(environment,
            deduceEnvironmentClass());
   }
   ConfigurationPropertySources.attach(environment);
   return environment;
}
```

org.springframework.boot.context.properties.source.ConfigurationPropertySources#attach

```java
public static void attach(Environment environment) {
   Assert.isInstanceOf(ConfigurableEnvironment.class, environment);
   MutablePropertySources sources = ((ConfigurableEnvironment) environment).getPropertySources();
   PropertySource<?> attached = sources.get(ATTACHED_PROPERTY_SOURCE_NAME);
   if (attached != null && attached.getSource() != sources) {
      sources.remove(ATTACHED_PROPERTY_SOURCE_NAME);
      attached = null;
   }
   if (attached == null) {
      sources.addFirst(new ConfigurationPropertySourcesPropertySource(ATTACHED_PROPERTY_SOURCE_NAME,
            new SpringConfigurationPropertySources(sources)));
   }
}
```

第一个sources，优先级最高

ConfigurationPropertySourcesPropertySource



## 配置优先级

ConfigurationPropertySourcesPropertySource {name='configurationProperties'}

StubPropertySource {name='servletConfigInitParams'}

ServletContextPropertySource {name='servletContextInitParams'}

PropertiesPropertySource {name='systemProperties'}

OriginAwareSystemEnvironmentPropertySource {name='systemEnvironment'}

RandomValuePropertySource {name='random'}

OriginTrackedMapPropertySource {name='applicationConfig: [classpath:/application.properties]'}

MapPropertySource {name='springCloudClientHostInfo'}MapPropertySource {name='defaultProperties'}