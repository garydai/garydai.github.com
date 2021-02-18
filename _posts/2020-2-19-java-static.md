---
date: 2020-2-19
layout: default
title: java-static


---

# Java内部类要设计成静态和非静态两种

内部类：就是我是你的一部分，我了解你，我知道你的全部，没有你就没有我。（所以内部类对象是以外部类对象存在为前提的）　　

静态内部类：就是我跟你没关系，自己可以完全独立存在，但是我就借你的壳用一下，来隐藏自己。

内部类是定义在另外一个类中的类，主要原因有：

- 内部类方法可以访问该类定义所在的作用域中的数据，包括私有的数据
- 内部类可以对同一个包的其他类隐藏

静态内部类和非静态内部类最大的区别是：非静态内部类编译后隐式保存着外部类的引用（就算外部类对象没用了也GC不掉），但是静态内部类没有。

```java
class OuterClass {
    ...
    static class StaticNestedClass {
        ...
    }
    class InnerClass {
        ...
    }
}
```



Nested classes are divided into two categories: static and non-static. Nested classes that are declared static are called ***static nested classes***. Non-static nested classes are called ***inner classes***.

```java
public class ShadowTest {

    public int x = 0;

    class FirstLevel {

        public int x = 1;

        void methodInFirstLevel(int x) {
            System.out.println("x = " + x);
            System.out.println("this.x = " + this.x);
            System.out.println("ShadowTest.this.x = " + ShadowTest.this.x);
        }
    }

    public static void main(String... args) {
        ShadowTest st = new ShadowTest();
        ShadowTest.FirstLevel fl = st.new FirstLevel();
        fl.methodInFirstLevel(23);
    }
}
```

The following is the output of this example:

```
x = 23
this.x = 1
ShadowTest.this.x = 0
```

Compelling reasons for using nested classes include the following:

- **It is a way of logically grouping classes that are only used in one place**: If a class is useful to only one other class, then it is logical to embed it in that class and keep the two together. Nesting such "helper classes" makes their package more streamlined.
- **It increases encapsulation**: Consider two top-level classes, A and B, where B needs access to members of A that would otherwise be declared `private`. By hiding class B within class A, A's members can be declared private and B can access them. In addition, B itself can be hidden from the outside world.
- **It can lead to more readable and maintainable code**: Nesting small classes within top-level classes places the code closer to where it is used.

用内部类只和外部类相关，放一起显得很合理



Inner类的实例有Outer的实例的指针（即可以访问Outer的成员）。而StaticInner类没有。

首先来看一下静态内部类的特点：静态内部类，只不过是想借你的外壳用一下。本身来说，我和你没有什么“强依赖”上的关系。没有你，我也可以创建实例。那么，在设计内部类的时候我们就可以做出权衡：如果我内部类与你外部类关系不紧密，耦合程度不高，不需要访问外部类的所有属性或方法，那么我就设计成静态内部类。而且，由于静态内部类与外部类并不会保存相互之间的引用，因此在一定程度上，还会节省那么一点内存资源，何乐而不为呢

既然上面已经说了什么时候应该用静态内部类，那么如果你的需求不符合静态内部类所提供的一切好处，你就应该考虑使用内部类了。最大的特点就是：你在内部类中需要访问有关外部类的所有属性及方法，我知晓你的一切



## reference

https://www.zhihu.com/question/28197253

https://docs.oracle.com/javase/tutorial/java/javaOO/nested.html

https://www.cnblogs.com/GrimMjx/p/10105626.html