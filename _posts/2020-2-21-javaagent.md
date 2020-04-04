---
date: 2020-2-21
layout: default
title: javaagent
---

# javaagent

启动时加载的 JavaAgent 是 JDK1.5 之后引入的新特性，**此特性为用户提供了在 JVM 将字节码文件读入内存之后，JVM 使用对应的字节流在 Java 堆中生成一个 Class 对象之前，用户可以对其字节码进行修改的能力**，从而 JVM 也将会使用用户修改过之后的字节码进行 Class 对象的创建。



Javaagent是java命令的一个参数。参数 javaagent 可以用于指定一个 jar 包，并且对该 java 包有2个要求：

1. 这个 jar 包的 MANIFEST.MF 文件必须指定 Premain-Class 项。
2. Premain-Class 指定的那个类必须实现 premain() 方法。

premain 方法，从字面上理解，就是运行在 main 函数之前的类。当Java 虚拟机启动时，在执行 main 函数之前，JVM 会先运行`-javaagent`所指定 jar 包内 Premain-Class 这个类的 premain 方法 。



从名字上看，似乎是个 Java 代理之类的，而实际上，他的功能更像是一个Class 类型的转换器，他可以在运行时接受重新外部请求，对Class类型进行修改



大部分类加载都会通过该方法，注意：是大部分，不是所有。当然，遗漏的主要是系统类，因为很多系统类先于 agent 执行，而用户类的加载肯定是会被拦截的。也就是说，这个方法是在 main 方法启动前拦截大部分类的加载活动，既然可以拦截类的加载，那么就可以去做重写类这样的操作，结合第三方的字节码编译工具，比如ASM，javassist，cglib等等来改写实现类。

```java
public class TestTransformer implements ClassFileTransformer {  
  @Override  
  public byte[] transform(ClassLoader classLoader, String className, Class<?> classBeingRedefined, ProtectionDomain protectionDomain, byte[] classfileBuffer) {  
        // 进行对应类字节码的操作，并返回新字节码数据的 byte 数组，如果返回 null，则代码不对此字节码作任何操作
        return null;
   } 
} 

```



例子：

```java
public class AgentMainTest {

    public static void agentmain(String agentArgs, Instrumentation instrumentation) {
        instrumentation.addTransformer(new MyClassTransformer(), true);
    }
  
   	public static void premain(String agentArgs, Instrumentation inst) {
        System.out.println("agentArgs : " + agentArgs);
        inst.addTransformer(new MyClassTransformer(), true);
    }
   
}
```



```java
package com.rickiyang.learn;

import javassist.*;

import java.io.IOException;
import java.lang.instrument.ClassFileTransformer;
import java.security.ProtectionDomain;

/**
 * @author rickiyang
 * @date 2019-08-06
 * @Desc
 */
public class MyClassTransformer implements ClassFileTransformer {
    @Override
    public byte[] transform(final ClassLoader loader, final String className, final Class<?> classBeingRedefined,final ProtectionDomain protectionDomain, final byte[] classfileBuffer) {
        // 操作Date类
        if ("java/util/Date".equals(className)) {
            try {
                // 从ClassPool获得CtClass对象
                final ClassPool classPool = ClassPool.getDefault();
                final CtClass clazz = classPool.get("java.util.Date");
                CtMethod convertToAbbr = clazz.getDeclaredMethod("convertToAbbr");
                //这里对 java.util.Date.convertToAbbr() 方法进行了改写，在 return之前增加了一个 打印操作
                String methodBody = "{sb.append(Character.toUpperCase(name.charAt(0)));" +
                        "sb.append(name.charAt(1)).append(name.charAt(2));" +
                        "System.out.println(\"sb.toString()\");" +
                        "return sb;}";
                convertToAbbr.setBody(methodBody);

                // 返回字节码，并且detachCtClass对象
                byte[] byteCode = clazz.toBytecode();
                //detach的意思是将内存中曾经被javassist加载过的Date对象移除，如果下次有需要在内存中找不到会重新走javassist加载
                clazz.detach();
                return byteCode;
            } catch (Exception ex) {
                ex.printStackTrace();
            }
        }
        // 如果返回null则字节码不会被修改
        return null;
    }
}
```

## 底层实现

- 创建并初始化JPLISAgent
- 监听VMInit事件，在vm初始化完成之后做下面的事情：
  - 创建InstrumentationImpl对象
  - 监听ClassFileLoadHook事件
  - 调用InstrumentationImpl的`loadClassAndCallPremain`方法，在这个方法里会去调用javaagent里MANIFEST.MF里指定的`Premain-Class`类的premain方法
- 解析javaagent里MANIFEST.MF里的参数，并根据这些参数来设置JPLISAgent里的一些内容

在加载类文件的时候发出ClassFileLoad的事件，然后交给instrumenat agent来调用javaagent里注册的ClassFileTransformer实现字节码的修改。

## jvm启动后动态instrument

上面介绍的Instrumentation是在 JDK 1.5中提供的，开发者只能在main加载之前添加手脚，在 Java SE 6 的 Instrumentation 当中，提供了一个新的代理操作方法：agentmain，可以在 main 函数开始运行之后再运行。



实际上是启动了一个socket进程去传输agent.jar。

## 引用

https://www.cnblogs.com/rickiyang/p/11368932.html

https://www.infoq.cn/article/fH69pYPqZPF6Cj1UJy7X



