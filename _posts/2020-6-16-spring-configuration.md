---
date: 2020-6-16
layout: default
title: spring配置管理

---

# spring配置管理

外部化配置的几种资源类型，除了 `properties` 和 `YAML` 外，还有环境变量、系统属性、启动参数等。所有的资源类型将近二十种。



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
     //将ConfigurationPropertySourcesPropertySource放到sources第一位
      sources.addFirst(new ConfigurationPropertySourcesPropertySource(ATTACHED_PROPERTY_SOURCE_NAME,
            new SpringConfigurationPropertySources(sources)));
   }
}
```

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

MapPropertySource {name='springCloudClientHostInfo'}

MapPropertySource {name='defaultProperties'}



`ConfigFileApplicationListener` 的监听器，监听ApplicationEnvironmentPreparedEvent事件后会进行加载 `application` 和 `YAML` 配置文件的操作

```java
public class ConfigFileApplicationListener implements EnvironmentPostProcessor, SmartApplicationListener, Ordered {
    
    ...
    
    private static final String DEFAULT_SEARCH_LOCATIONS = "classpath:/,classpath:/config/,file:./,file:./config/";
    
    public static final String CONFIG_NAME_PROPERTY = "spring.config.name";

	public static final String CONFIG_LOCATION_PROPERTY = "spring.config.location";
    
    public static final String CONFIG_ADDITIONAL_LOCATION_PROPERTY = "spring.config.additional-location";
    
    private static final String DEFAULT_NAMES = "application";
    
    @Override
	public void onApplicationEvent(ApplicationEvent event) {
	    // 1、通过 instanceof 判断事件的类型，如果是 ApplicationEnvironmentPreparedEvent 事件，则执行 onApplicationEnvironmentPreparedEvent 方法
		if (event instanceof ApplicationEnvironmentPreparedEvent) {
			onApplicationEnvironmentPreparedEvent((ApplicationEnvironmentPreparedEvent) event);
		}
		...
	}
	
	private void onApplicationEnvironmentPreparedEvent(ApplicationEnvironmentPreparedEvent event) {
		// 2、调用 loadPostProcessors 方法，返回 Environment 的后置处理器集合，我们跳到 2.1 查看方法实现
		List<EnvironmentPostProcessor> postProcessors = loadPostProcessors();
		
		// 2.2、把自己也加入该集合
		postProcessors.add(this);
		AnnotationAwareOrderComparator.sort(postProcessors);
		
		// 2.3、遍历 EnvironmentPostProcessor 集合，执行它们的 postProcessEnvironment 方法，我们跳到 3 查看当前类的该方法实现
		for (EnvironmentPostProcessor postProcessor : postProcessors) {
			postProcessor.postProcessEnvironment(event.getEnvironment(), event.getSpringApplication());
		}
	}
	
	// 2.1 是我们比较熟悉的 loadFactories 方法，在 Spring Boot 自动装配（二） 的 2.1.2 小节讲过，loadFactories 方法是从 spring.factories 文件中加载 key 为 EnvironmentPostProcessor 的实现类集合
	List<EnvironmentPostProcessor> loadPostProcessors() {
		return SpringFactoriesLoader.loadFactories(EnvironmentPostProcessor.class, getClass().getClassLoader());
	}
	
	// 3、 执行到该方法时，会调用 addPropertySources 方法，入参是上文加载 ConfigurableEnvironment 对象
	@Override
	public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
		addPropertySources(environment, application.getResourceLoader());
	}
	
	protected void addPropertySources(ConfigurableEnvironment environment, ResourceLoader resourceLoader) {
		RandomValuePropertySource.addToEnvironment(environment);
		
		// 4、 我们主要关注这里，通过 Loader 的构造方法创建该对象，并调用它的 load 方法
		new Loader(environment, resourceLoader).load();
	}
	
	private class Loader {
	
	    private final ConfigurableEnvironment environment;
	    
	    private final List<PropertySourceLoader> propertySourceLoaders;
	
	    // 4.1、 构造方法中会初始化一些属性
	    Loader(ConfigurableEnvironment environment, ResourceLoader resourceLoader) {
			...
			this.environment = environment;
			
			// 又是我们比较熟悉的 loadFactories 方法，在 Spring Boot 自动装配（二） 的 2.1.2 小节讲过，loadFactories 方法是从 spring.factories 文件中加载 key 为 PropertySourceLoader 的实现类集合。这里加载的是 PropertiesPropertySourceLoader 和 YamlPropertySourceLoader 两个实现类，看类名可初步断定是处理 properties 和 YAML 文件的
			this.propertySourceLoaders = SpringFactoriesLoader.loadFactories(PropertySourceLoader.class,getClass().getClassLoader());
		}
		
		public void load() {
			...
			// 5、这里会继续调用它重载的 load 方法
			load(null, this::getNegativeProfileFilter, addToLoaded(MutablePropertySources::addFirst, true));
			...
			
			// 9、这是最后一步，将当前类中的 MutablePropertySources 中的 PropertySource 对象，全部塞到 ConfigurableEnvironment 的 MutablePropertySources 对象中。我们跳到 9.1 进行查看
			addLoadedPropertySources();
		}
		
		private void load(Profile profile, DocumentFilterFactory filterFactory, DocumentConsumer consumer) {
			
			// 5.1、首先执行 getSearchLocations 方法，看方法名大致能猜出是获取搜索路径的，我们跳到 5.1.1 查看该方法的实现
			getSearchLocations().forEach((location) -> {
			
			    // 5.2、开始遍历该集合，先判断该路径是否是以反斜杠结尾，是的话则该路径为文件夹；不是的话，则该路径为文件的完整路径，类似于 classPath:/application.properties 
				boolean isFolder = location.endsWith("/");
				
				// 5.3、 如果是文件夹路径，则通过 getSearchNames 获取文件的名称，不是则返回空集合，我们跳到 5.3.1 查看 getSearchNames 方法
				Set<String> names = isFolder ? getSearchNames() : NO_SEARCH_NAMES;
				
				// 5.4、再调用 load 的重载方法，这里，location 是路径名，name是文件名，我们跳到 6 进行查看
				names.forEach((name) -> load(location, name, profile, filterFactory, consumer));
			});
		}
		
		// 5.1.1、这个方法就是获取加载 application 和 YAML 文件路径的
		private Set<String> getSearchLocations() {
		
		    //  可以看到 CONFIG_LOCATION_PROPERTY 的值为 spring.config.location，也就是说，先判断我们有没有手动设置搜索路径，有的话直接返回该路径。该值一般通过启动参数的方式设置
			if (this.environment.containsProperty(CONFIG_LOCATION_PROPERTY)) {
				return getSearchLocations(CONFIG_LOCATION_PROPERTY);
			}
			
			// 该 CONFIG_ADDITIONAL_LOCATION_PROPERTY 变量的值为 spring.config.additional-location，这也是用于手动设置搜索路径，不过和上面不同的是，不会覆盖 接下来默认的搜索路径
			Set<String> locations = getSearchLocations(CONFIG_ADDITIONAL_LOCATION_PROPERTY);
			
			// 这里就是获取默认的搜索路径，通过 DEFAULT_SEARCH_LOCATIONS 变量的值 classpath:/,classpath:/config/,file:./,file:./config/，将该值用逗号分隔，加入集合并返回。到这一步，我们至少获取到了4个加载 application 和 YAML 文件的路径
			locations.addAll(asResolvedSet(ConfigFileApplicationListener.this.searchLocations, DEFAULT_SEARCH_LOCATIONS));
			return locations;
		}
		
		// 5.3.1 
		private Set<String> getSearchNames() {
		
		    // CONFIG_LOCATION_PROPERTY 变量值为 spring.config.name ，同样先判断有没有手动设置文件名称，有的话，直接返回
			if (this.environment.containsProperty(CONFIG_NAME_PROPERTY)) {
				String property = this.environment.getProperty(CONFIG_NAME_PROPERTY);
				return asResolvedSet(property, null);
			}
			
			// 如果没有，则通过 DEFAULT_NAMES 变量值返回默认的文件名，变量值为 application
			return asResolvedSet(ConfigFileApplicationListener.this.names, DEFAULT_NAMES);
		}
		
		// 6、
		private void load(String location, String name, Profile profile, DocumentFilterFactory filterFactory,
				DocumentConsumer consumer) {
				
			// 6.1、 上面 5.2 说过 name 为空时，表示 location 是完整的文件路径。之后进入这个 if 
			if (!StringUtils.hasText(name)) {
			
			    // 6.1.1、propertySourceLoaders 属性是在 4.1 处被初始化的，存储的是 PropertiesPropertySourceLoader 和 YamlPropertySourceLoader 两个类。这里对这两个类进行遍历
				for (PropertySourceLoader loader : this.propertySourceLoaders) {
				
				    // 我们跳到 6.1.2 查看 canLoadFileExtension 方法实现，入参 location 是文件的完整路径
					if (canLoadFileExtension(loader, location)) {
						
						// 这里又是一个 load 重载方法，我们跳到 7 进行查看
						load(loader, location, profile, filterFactory.getDocumentFilter(profile), consumer);
						return;
					}
				}
			}
			Set<String> processed = new HashSet<>();
			for (PropertySourceLoader loader : this.propertySourceLoaders) {
			
			    // 6.2 这里和 6.1.3 类似，获取文件扩展名
				for (String fileExtension : loader.getFileExtensions()) {
					if (processed.add(fileExtension)) {
						
						// 进入 6.3、查看该方法实现。关注重点的两个参数：一个是路径名 + 文件名，还有一个 “.” +文件扩展名
						loadForFileExtension(loader, location + name, "." + fileExtension, profile, filterFactory,
								consumer);
					}
				}
			}
		}
		
		// 6.1.2、 该方法作用是 判断 name 完整路径名是否以指定的文件扩展名结尾
		private boolean canLoadFileExtension(PropertySourceLoader loader, String name) {
		
		    // 6.1.3、调用 PropertySourceLoader 的 getFileExtensions 方法。当你的实现类是 PropertiesPropertySourceLoader 时，该方法返回 properties、xml；如果是 YamlPropertySourceLoader 则返回 yml、yaml。从这里可以看出，能被处理的文件格式有这四种
			return Arrays.stream(loader.getFileExtensions())
					.anyMatch((fileExtension) -> StringUtils.endsWithIgnoreCase(name, fileExtension));
		}
		
		// 6.3 到了这里，prefix 和 fileExtension 都是进行拼接好的值，如 prefix = classpath:/applicarion，fileExtension = .properties
		private void loadForFileExtension(PropertySourceLoader loader, String prefix, String fileExtension,
				Profile profile, DocumentFilterFactory filterFactory, DocumentConsumer consumer) {
			
			...
			
			// 这里同样调用节点 7 的重载方法，通过 prefix + fileExtension 形成完整的文件路径名，通过入参进行传递。如 classpath:/applicarion.properties
			load(loader, prefix + fileExtension, profile, profileFilter, consumer);
		}
		
		// 7、
		private void load(PropertySourceLoader loader, String location, Profile profile, DocumentFilter filter,
				DocumentConsumer consumer) {
			try {
			
			    // 这里调用 ResourceLoader 的 getResource 方法，通过 location 文件路径，读取获取该文件资源，之后就好办了
				Resource resource = this.resourceLoader.getResource(location);
				
				...
				
				// 具体解析在过程 loadDocuments 中，这里就不继续跟踪了，大致是以流的方式解析文件。解析之后会生成一个 PropertySource 对象，该对象在上面说过，表示一个外部化配置源对象，存储配置中的数据。之后，会将该对象封装到 Document 中
				List<Document> documents = loadDocuments(loader, name, resource);
				
				...
				
				if (!loaded.isEmpty()) {
				
				    // 遍历 documents 集合，当执行 consumer.accept 时会进入 addToLoaded 方法，这是 Java8 的写法。consumer 对象参数来自节点 5 。我们跳到 8 查看 addToLoaded 实现
					loaded.forEach((document) -> consumer.accept(profile, document));
					if (this.logger.isDebugEnabled()) {
						StringBuilder description = getDescription("Loaded config file ", location, resource, profile);
						this.logger.debug(description);
					}
				}
			}
			catch (Exception ex) {
				throw new IllegalStateException("Failed to load property " + "source from location '" + location + "'",
						ex);
			}
		}
		
		// 8、BiConsumer 是 JAVA8 的函数接口，表示定义一个带有两个参数且不返回结果的操作，通过节点 5 我们知道，这个操作是 MutablePropertySources::addFirst 。
		private DocumentConsumer addToLoaded(BiConsumer<MutablePropertySources, PropertySource<?>> addMethod,
				boolean checkForExisting) {
			return (profile, document) -> {
				if (checkForExisting) {
					for (MutablePropertySources merged : this.loaded.values()) {
						if (merged.contains(document.getPropertySource().getName())) {
							return;
						}
					}
				}
				MutablePropertySources merged = this.loaded.computeIfAbsent(profile,
						(k) -> new MutablePropertySources());
						
				// 当调用 BiConsumer 的 accept 方法时，定义的操作会执行，两个入参分别是 MutablePropertySources 对象和配置文件源对象 PropertySource。该操作会调用 MutablePropertySources 的 addFirst 方法把该配置文件源对象添加至其中。最后我们去看看前面 load 方法中的最后一步 9
				addMethod.accept(merged, document.getPropertySource());
			};
		}
		
		// 9.1
		private void addLoadedPropertySources() {
		
		    // 获取当前上下文环境中的 MutablePropertySources 对象
			MutablePropertySources destination = this.environment.getPropertySources();
			
			// 获取当前类中的 MutablePropertySources 集合
			List<MutablePropertySources> loaded = new ArrayList<>(this.loaded.values());
			Collections.reverse(loaded);
			String lastAdded = null;
			Set<String> added = new HashSet<>();
			
			// 遍历 loaded 集合及其中所有的 PropertySource ，也就是 application 或 YAML 配置文件源对象
			for (MutablePropertySources sources : loaded) {
				for (PropertySource<?> source : sources) {
					if (added.add(source.getName())) {
					
					    // 我们进入 9.2 查看该方法，主要参数是上下文环境中的 MutablePropertySources 对象和配置文件源对象
						addLoadedPropertySource(destination, lastAdded, source);
						lastAdded = source.getName();
					}
				}
			}
		}

        // 9.2 
		private void addLoadedPropertySource(Mutab lePropertySources destination, String lastAdded,
				PropertySource<?> source) {
			if (lastAdded == null) {
				if (destination.contains(DEFAULT_PROPERTIES)) {
					destination.addBefore(DEFAULT_PROPERTIES, source);
				}
				else {
					destination.addLast(source);
				}
			}
			else {
			
			    // 最后通过将 source 添加到 environment 中的 MutablePropertySources 对象中。
				destination.addAfter(lastAdded, source);
			}
		}
		
		// 至此，properties 和 YAML 配置文件就被加载到了上下文环境共享的 Environment 中，之后如 @Value 等获取值都是从该对象中获取
	}
}
```

可以看到，`ConfigFileApplicationListener` 主要功能就是将 `properties` 和 `YAML` 文件加载到 `Environment` 中。另外还存在一个 `@PropertySource` 注解，也是加载指定的配置文件到 `Environment` 中。



还有一种配置

```java
@ConfigurationProperties(prefix = "spring.redis")
public class RedisProperties {
    private String url;

	private String host = "localhost";

	private String password;

	private int port = 6379;
	
	...
}
```



```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Import(EnableConfigurationPropertiesImportSelector.class)
public @interface EnableConfigurationProperties {

	/**
	 * Convenient way to quickly register {@link ConfigurationProperties} annotated beans
	 * with Spring. Standard Spring Beans will also be scanned regardless of this value.
	 * @return {@link ConfigurationProperties} annotated beans to register
	 */
	Class<?>[] value() default {};

}
```

```java
class EnableConfigurationPropertiesImportSelector implements ImportSelector {

	private static final String[] IMPORTS = { ConfigurationPropertiesBeanRegistrar.class.getName(),
			ConfigurationPropertiesBindingPostProcessorRegistrar.class.getName() };

	@Override
	public String[] selectImports(AnnotationMetadata metadata) {
		return IMPORTS;
	}

	...
}
```

`ConfigurationPropertiesBeanRegistrar` 就是用来注册 `Properties` 配置类的，而 `ConfigurationPropertiesBindingPostProcessorRegistrar` 则是用来绑定配置属性

如果一个配置类只配置@ConfigurationProperties注解，而没有使用@Component，那么在IOC容器中是获取不到properties 配置文件转化的bean或使用@EnableConfigurationProperties(xxx.class)



当我们使用 `@ConfigurationProperties` 时，无需标注 `@EnableConfigurationProperties` 注解，因为 `Spring Boot` 在自动装配的过程中会帮我们加载一个名为 `ConfigurationPropertiesAutoConfiguration` 的类，该类是在 `spring.factories` 中定义好的：

```java
# Auto Configure
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration
```

```java
@Configuration
@EnableConfigurationProperties
public class ConfigurationPropertiesAutoConfiguration {

}
```



## 参考

https://www.cnblogs.com/loongk/p/12046582.html?ivk_sa=1024320u

