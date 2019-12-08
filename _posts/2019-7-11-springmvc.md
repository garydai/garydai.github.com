---
layout: default

title: springmvc

---

## springmvc

### 初始化
load所有controller、service等注解，放入ioc容器

将单例注入类中变量（例如@autowried注释的变量）

handlermapping（根据@RequestMapping注解将url路径关联到对应类的对应方法）





```java
public abstract class AbstractHandlerMethodMapping<T> extends AbstractHandlerMapping implements InitializingBean {
  
	org.springframework.web.servlet.handler.AbstractHandlerMethodMapping#afterPropertiesSet->org.springframework.web.servlet.handler.AbstractHandlerMethodMapping#initHandlerMethods

	将uri mapping到方法
    
    protected void initHandlerMethods() {
		if (logger.isDebugEnabled()) {
			logger.debug("Looking for request mappings in application context: " + getApplicationContext());
		}
    // 获取spring容器里的所有bean
		String[] beanNames = (this.detectHandlerMethodsInAncestorContexts ?
				BeanFactoryUtils.beanNamesForTypeIncludingAncestors(obtainApplicationContext(), Object.class) :
				obtainApplicationContext().getBeanNamesForType(Object.class));

		for (String beanName : beanNames) {
			if (!beanName.startsWith(SCOPED_TARGET_NAME_PREFIX)) {
				Class<?> beanType = null;
				try {
					beanType = obtainApplicationContext().getType(beanName);
				}
				catch (Throwable ex) {
					// An unresolvable bean type, probably from a lazy bean - let's ignore it.
					if (logger.isDebugEnabled()) {
						logger.debug("Could not resolve target class for bean with name '" + beanName + "'", ex);
					}
				}
        // 提取有Controller.class和RequestMapping注解的bean
				if (beanType != null && isHandler(beanType)) {
          // 找到类里所有RequestMapping注解的方法，映射uri和方法信息
					detectHandlerMethods(beanName);
				}
			}
		}
		handlerMethodsInitialized(getHandlerMethods());
	}
}
```



