# Loom / Tauri Android — 防止 R8 混淆导致启动闪退
# 11.x WebView + Tauri JNI 桥不能被裁剪

# Tauri / WRY / JNI
-keep class com.tauri.** { *; }
-keep class app.tauri.** { *; }
-keep class tauri.** { *; }
-keep class wry.** { *; }
-keep class wu.jiu.** { *; }
-keep class app.loom.shell.** { *; }
-keep class app.loom.shell.MainActivity { *; }
-keep class app.loom.shell.TauriActivity { *; }

# 保留 native 方法与 JNI 注册
-keepclasseswithmembernames class * {
    native <methods>;
}
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
-keepattributes JavascriptInterface
-keepattributes *Annotation*
-keepattributes SourceFile,LineNumberTable
-keepattributes InnerClasses,EnclosingMethod

# Kotlin / coroutines
-keep class kotlin.** { *; }
-keep class kotlinx.** { *; }
-dontwarn kotlin.**
-dontwarn kotlinx.**

# WebView
-keep class android.webkit.** { *; }
-dontwarn android.webkit.**

# 签名 / keystore 相关勿混淆入口
-keep class androidx.core.content.FileProvider { *; }
