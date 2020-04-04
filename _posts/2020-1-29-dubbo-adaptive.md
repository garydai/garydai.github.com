---
date: 2020-1-29
layout: default
title: dubbo-adaptive
---

# dubbo-adaptive

一个接口有多个实现类，如何在运行时动态决定，注入哪个实现类

## dubbo

通过生成接口的代理类，然后注入代理类，代理类会通过URL参数，决定使用哪个实现类。

注入一个有多个实现类的接口，由注解adaptive的value值决定，把这个value作为一个参数，从URL里找到对应的参数值，将这个参数值作为key，从容器里找到对应实现类的实例

```java
@SPI("impl1")
public interface SimpleExt {
    // @Adaptive example, do not specify a explicit key.
    @Adaptive
    String echo(URL url, String s);

    @Adaptive({"key1", "key2"})
    String yell(URL url, String s);

    // no @Adaptive
    String bang(URL url, int i);
}
```

```java

   			public void test_getAdaptiveExtension_defaultAdaptiveKey() throws Exception {
        {
          //SinpleExt$Adaptive
            SimpleExt ext = ExtensionLoader.getExtensionLoader(SimpleExt.class).getAdaptiveExtension();

            Map<String, String> map = new HashMap<String, String>();
            URL url = new URL("p1", "1.2.3.4", 1010, "path1", map);

            String echo = ext.echo(url, "haha");
            assertEquals("Ext1Impl1-echo", echo);
        }

        {
            SimpleExt ext = ExtensionLoader.getExtensionLoader(SimpleExt.class).getAdaptiveExtension();

            Map<String, String> map = new HashMap<String, String>();
            map.put("simple.ext", "impl2");
            URL url = new URL("p1", "1.2.3.4", 1010, "path1", map);

            String echo = ext.echo(url, "haha");
            assertEquals("Ext1Impl2-echo", echo);
        }
    }
```

```java
package org.apache.dubbo.common.extension.ext1;
import org.apache.dubbo.common.extension.ExtensionLoader;

public class SimpleExt$Adaptive implements org.apache.dubbo.common.extension.ext1.SimpleExt {
    public java.lang.String yell(org.apache.dubbo.common.URL arg0, java.lang.String arg1) {
        if (arg0 == null) throw new IllegalArgumentException("url == null");
        org.apache.dubbo.common.URL url = arg0;
        String extName = url.getParameter("key1", url.getParameter("key2", "impl1"));
        if (extName == null)
            throw new IllegalStateException("Failed to get extension (org.apache.dubbo.common.extension.ext1.SimpleExt) name from url (" + url.toString() + ") use keys([key1, key2])");
        org.apache.dubbo.common.extension.ext1.SimpleExt extension = (org.apache.dubbo.common.extension.ext1.SimpleExt) ExtensionLoader.getExtensionLoader(org.apache.dubbo.common.extension.ext1.SimpleExt.class).getExtension(extName);
        return extension.yell(arg0, arg1);
    }

    public java.lang.String echo(org.apache.dubbo.common.URL arg0, java.lang.String arg1) {
        if (arg0 == null) throw new IllegalArgumentException("url == null");
        org.apache.dubbo.common.URL url = arg0;
        String extName = url.getParameter("simple.ext", "impl1");
        if (extName == null)
            throw new IllegalStateException("Failed to get extension (org.apache.dubbo.common.extension.ext1.SimpleExt) name from url (" + url.toString() + ") use keys([simple.ext])");
        org.apache.dubbo.common.extension.ext1.SimpleExt extension = (org.apache.dubbo.common.extension.ext1.SimpleExt) ExtensionLoader.getExtensionLoader(org.apache.dubbo.common.extension.ext1.SimpleExt.class).getExtension(extName);
        return extension.echo(arg0, arg1);
    }

    public java.lang.String bang(org.apache.dubbo.common.URL arg0, int arg1) {
        throw new UnsupportedOperationException("The method public abstract java.lang.String org.apache.dubbo.common.extension.ext1.SimpleExt.bang(org.apache.dubbo.common.URL,int) of interface org.apache.dubbo.common.extension.ext1.SimpleExt is not adaptive method!");
    }
}
```

## spring

怎么实现dubbo这种功能？

