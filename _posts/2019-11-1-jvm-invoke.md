---
date: 2019-11-1
layout: default
title: jvm-invoke
---

# java函数调用

因为某个类中的重载方法可能被它的子类所重写，因此Java 编译器会将所有对非私有实例方法的调用编译为需要动态绑定的类型

Java 虚拟机中的静态绑定指的是在解析时便能够直接识别目标方法的情况，而动态绑定则指的是需要在运行过程中根据调用者的动态类型来识别目标方法的情况

```
invokestatic：用于调用静态方法。
invokespecial：用于调用私有实例方法、构造器，以及使用 super 关键字调用父类的实例方法或构造器，和所实现接口的默认方法。
invokevirtual：用于调用非私有实例方法。
invokeinterface：用于调用接口方法。
invokedynamic：用于调用动态方法。
```

对于 invokestatic 以及 invokespecial 而言，Java 虚拟机能够直接识别具体的目标方法。而对于 invokevirtual 以及 invokeinterface 而言，在绝大部分情况下，虚拟机需要在执行过程中，根据调用者的动态类型，来确定具体的目标方法。除了final标记的函数

在编译过程中，我们并不知道目标方法的具体内存地址。因此，Java 编译器会暂时用符号引用来表示该目标方法。这一符号引用包括目标方法所在的类或接口的名字，以及目标方法的方法名和方法描述符。

符号引用存储在 class 文件的常量池之中

在 class 文件中，Java 编译器会用符号引用指代目标方法。在执行调用指令前，它所附带的符号引用需要被解析成实际引用。对于可以静态绑定的方法调用而言，实际引用为目标方法的指针。对于需要动态绑定的方法调用而言，实际引用为辅助动态绑定的信息。

两个方法的参数类型一致，编译器会认为是重写，但只有当两个方法的参数类型以及返回类型一致时，Java 虚拟机才会判定为重写。



## 找出方法

对于非接口符号引用，假定该符号引用所指向的类为 C，则 Java 虚拟机会按照如下步骤进行查找。

1. 在 C 中查找符合名字及描述符的方法。
2. 如果没有找到，在 C 的父类中继续搜索，直至 Object 类。
3. 如果没有找到，在 C 所直接实现或间接实现的接口中搜索，这一步搜索得到的目标方法必须是非私有、非静态的。并且，如果目标方法在间接实现的接口中，则需满足 C 与该接口之间没有其他符合条件的目标方法。如果有多个符合条件的目标方法，则任意返回其中一个。

对于接口符号引用，假定该符号引用所指向的接口为 I，则 Java 虚拟机会按照如下步骤进行查找。

1. 在 I 中查找符合名字及描述符的方法。
2. 如果没有找到，在 Object 类中的公有实例方法中搜索。
3. 如果没有找到，则在 I 的超接口中搜索。这一步的搜索结果的要求与非接口符号引用步骤 3 的要求一致。



经过上述的解析步骤之后，符号引用会被解析成实际引用。对于可以静态绑定的方法调用而言，实际引用是一个指向方法的指针。对于需要动态绑定的方法调用而言，实际引用则是一个方法表的索引

## 虚方法调用

Java 里所有非私有实例方法调用都会被编译成 invokevirtual 指令，而接口方法调用都会被编译成 invokeinterface 指令。这两种指令，均属于 Java 虚拟机中的虚方法调用。

## 方法表

类加载的准备阶段，它除了为静态字段分配内存之外，还会构造与该类相关联的方法表

invokevirtual 所使用的虚方法表（virtual method table，vtable）

invokeinterface 所使用的接口方法表（interface method table，itable）

子类方法表中包含父类方法表中的所有方法；

子类方法在方法表中的索引值，与它所重写的父类方法的索引值相同

方法调用指令中的符号引用会在执行之前解析成实际引用。对于静态绑定的方法调用而言，实际引用将指向具体的目标方法。对于动态绑定的方法调用而言，实际引用则是方法表的索引值（实际上并不仅是索引值）



```java

abstract class Passenger {
  abstract void passThroughImmigration();
  @Override
  public String toString() { ... }
}
class ForeignerPassenger extends Passenger {
   @Override
   void passThroughImmigration() { /* 进外国人通道 */ }
}
class ChinesePassenger extends Passenger {
  @Override
  void passThroughImmigration() { /* 进中国人通道 */ }
  void visitDutyFreeShops() { /* 逛免税店 */ }
}

Passenger passenger = ...
passenger.passThroughImmigration();

```

![image-20191101153748947](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20191101153748947.png)

使用了方法表的动态绑定与静态绑定相比，仅仅多出几个内存解引用操作：访问栈上的调用者，读取调用者的动态类型，读取该类型的方法表，读取方法表中某个索引值所对应的目标方法

即时编译还拥有另外两种性能更好的优化手段：内联缓存（inlining cache）和方法内联（method inlining）

内联缓存是一种加快动态绑定的优化技术。它能够缓存虚方法调用中调用者的动态类型，以及该类型所对应的目标方法。在之后的执行过程中，如果碰到已缓存的类型，内联缓存便会直接调用该类型所对应的目标方法。如果没有碰到已缓存的类型，内联缓存则会退化至使用基于方法表的动态绑定

## method invoke

方法反射Method.invoke源码

```java

public final class Method extends Executable {
  ...
  public Object invoke(Object obj, Object... args) throws ... {
    ... // 权限检查
    MethodAccessor ma = methodAccessor;
    if (ma == null) {
      ma = acquireMethodAccessor();
    }
    return ma.invoke(obj, args);
  }
}

```

委派给 MethodAccessor 来处理。MethodAccessor 是一个接口，它有两个已有的具体实现：一个通过本地方法来实现反射调用，另一个则使用了委派模式（生成动态代理类来执行方法）

```java

// 动态实现的伪代码，这里只列举了关键的调用逻辑，其实它还包括调用者检测、参数检测的字节码。
package jdk.internal.reflect;

public class GeneratedMethodAccessor1 extends ... {
  @Overrides    
  public Object invoke(Object obj, Object[] args) throws ... {
    Test.target((int) args[0]);
    return null;
  }
}
```

Java 虚拟机设置了一个阈值 15（可以通过 -Dsun.reflect.inflationThreshold= 来调整），当某个反射调用的调用次数在 15 之下时，采用本地实现；当达到 15 时，便开始动态生成字节码，并将委派实现的委派对象切换至动态实现，这个过程我们称之为 Inflation

## invokedynamic

```java

class Horse {
  public void race() {
    System.out.println("Horse.race()"); 
  }
}

class Deer {
  public void race() {
    System.out.println("Deer.race()");
  }
}

class Cobra {
  public void race() {
    System.out.println("How do you turn this on?");
  }
}
```

如何用同一种方式调用他们的赛跑方法?

Java 7 引入了一条新的指令 invokedynamic。该指令的调用机制抽象出调用点这一个概念，并允许应用程序将调用点链接至任意符合条件的方法上，在第一次执行 invokedynamic 指令时，Java 虚拟机将执行它所对应的启动方法，生成并且绑定一个调用点。之后如果再次执行该指令，Java 虚拟机则直接调用已经绑定了的调用点所链接的方法。

理想的调用方式

```java
public static void startRace(java.lang.Object)
       0: aload_0                // 加载一个任意对象
       1: invokedynamic race     // 调用赛跑方法

```



它将**调用点（CallSite）抽象成一个 Java 类**，并且将原本由 Java 虚拟机控制的方法调用以及方法链接暴露给了应用程序。在运行过程中，每一条 invokedynamic 指令将捆绑一个调用点，并且会调用该调用点所链接的方法句柄

### 方法句柄

方法句柄是一个强类型的、能够被直接执行的引用。它仅关心所指向方法的参数类型以及返回类型，而不关心方法所在的类以及方法名。方法句柄的权限检查发生在创建过程中，相较于反射调用节省了调用时反复权限检查的开销。

### 获取方法句柄两种方式

```java
class Foo {
  private static void bar(Object o) {
    ..
  }
  public static Lookup lookup() {
    return MethodHandles.lookup();
  }
}

// 获取方法句柄的不同方式
MethodHandles.Lookup l = Foo.lookup(); // 具备Foo类的访问权限
Method m = Foo.class.getDeclaredMethod("bar", Object.class);
MethodHandle mh0 = l.unreflect(m);

MethodType t = MethodType.methodType(void.class, Object.class);
MethodHandle mh1 = l.findStatic(Foo.class, "bar", t);
```

在 Java 8 中，Lambda 表达式也是借助 invokedynamic 来实现的

```java

int x = ..
IntStream.of(1, 2, 3).map(i -> i * 2).map(i -> i * x);



  // i -> i * 2
  private static int lambda$0(int);
    Code:
       0: iload_0
       1: iconst_2
       2: imul
       3: ireturn

  // i -> i * x
  private static int lambda$1(int, int);
    Code:
       0: iload_1
       1: iload_0
       2: imul
       3: ireturn
```

该 invokedynamic 指令对应的启动方法将通过 ASM 生成一个适配器类。

## reference

https://time.geekbang.org/column/article/12098

