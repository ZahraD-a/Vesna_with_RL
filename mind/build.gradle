defaultTasks 'run'

apply plugin: 'java'

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

repositories {
    maven { url "https://raw.githubusercontent.com/jacamo-lang/mvn-repo/master" }
    maven { url "https://repo.gradle.org/gradle/libs-releases" }
    mavenCentral()
}

dependencies {
    implementation ('org.jacamo:jacamo:1.2')

    // https://mvnrepository.com/artifact/org.java-websocket/Java-WebSocket
    implementation group: 'org.java-websocket', name: 'Java-WebSocket', version: '1.5.6'
    // https://mvnrepository.com/artifact/org.json/json
    implementation("org.json:json:20230227")
    
    // https://mvnrepository.com/artifact/javax.validation/validation-api
    implementation("javax.validation:validation-api:2.0.1.Final")

}

task run (type: JavaExec, dependsOn: 'classes') {
    description 'runs the application'
    group ' JaCaMo'
    mainClass = 'jacamo.infra.JaCaMoLauncher'
    args 'vesna.jcm'
    classpath sourceSets.main.runtimeClasspath
}

task runRL (type: JavaExec, dependsOn: 'classes') {
    description 'runs the RL agent'
    group ' JaCaMo'
    mainClass = 'jacamo.infra.JaCaMoLauncher'
    args 'vesna_rl.jcm'
    classpath sourceSets.main.runtimeClasspath
}

javadoc {
    destinationDir = file( "$buildDir/docs/javadoc" )
    options.memberLevel = JavadocMemberLevel.PRIVATE
    options.addStringOption( "-add-stylesheet", "styles.css" )
}

sourceSets {
    main {
        java {
            srcDir 'src/'
        }
    }
}
