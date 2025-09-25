# Upgrade to Java 21 (Temurin) for this project

This project requests Java 21 via Gradle toolchains in `android/app/build.gradle.kts`.
Your system currently has Java 8 as the default. To build with Java 21, install a JDK 21 and either let Gradle toolchains find it, or point Gradle to it explicitly.

The steps below assume Windows PowerShell (pwsh) and will install Eclipse Temurin (Adoptium) JDK 21 to `C:\Program Files\Eclipse Adoptium\jdk-21`.

1) Download and extract Temurin 21

```powershell
# Create a temp folder
$td = "$env:TEMP\temurin21"
New-Item -ItemType Directory -Path $td -Force | Out-Null

# Download Temurin 21 (x64 MSI or ZIP). Here we'll use the ZIP distribution from Adoptium.
$zipUrl = 'https://github.com/adoptium/temurin21-binaries/releases/latest/download/OpenJDK21U-jdk_x64_windows_hotspot.zip'
$zip = Join-Path $td 'temurin21.zip'
Invoke-WebRequest -Uri $zipUrl -OutFile $zip

# Extract to Program Files (requires admin privileges to write there)
$installDir = 'C:\\Program Files\\Eclipse Adoptium\\jdk-21'
if (-Not (Test-Path $installDir)) { New-Item -ItemType Directory -Path $installDir -Force | Out-Null }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $installDir)

# The archive may contain a single subfolder like 'jdk-21.0.1+...'; find it and move contents up
$sub = Get-ChildItem -Directory $installDir | Select-Object -First 1
if ($sub) {
    Get-ChildItem -Path $sub.FullName -Force | Move-Item -Destination $installDir -Force
    Remove-Item -Recurse -Force $sub.FullName
}

# Cleanup
Remove-Item -Path $zip -Force
Remove-Item -Path $td -Recurse -Force

# Show installed java
& "$installDir\\bin\\java.exe" -version
```

2) (Optional) Set `org.gradle.java.home` for this project

Open `android/gradle.properties` and set (uncomment) the path to the JDK home you installed. Example:

```
org.gradle.java.home=C:\\Program Files\\Eclipse Adoptium\\jdk-21
```

This pins Gradle to use that JDK for builds.

3) Verify Gradle build

From project root (PowerShell):

```powershell
# Use the wrapper to build the Android project
.\android\gradlew.bat -p android assembleDebug
```

Notes
- The Gradle wrapper in this repo is 8.12 and supports Java 21.
- CI runners (GitHub Actions, etc.) should also be updated to use JDK 21.
- If you prefer Oracle/OpenJDK builds, adapt the download URL above.

If you'd like, I can:
- Add a script to automate the install (requires admin privileges).
- Attempt to install JDK 21 on this machine now (I cannot because the automated install tool needs an upgraded plan).
- Update CI configs to install JDK 21.
