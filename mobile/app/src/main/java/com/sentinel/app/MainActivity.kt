package com.sentinel.app

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.BatteryManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

class MainActivity : ComponentActivity() {
    private lateinit var tracker: LocationTracker
    private val prefs by lazy { getSharedPreferences("sentinel", Context.MODE_PRIVATE) }
    private val scope = CoroutineScope(Dispatchers.Main)

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        if (permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true || permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true) tracker.start()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tracker = LocationTracker(this, { prefs.getString("device_id", null) }, { batteryLevel() })
        ApiClient.setToken(prefs.getString("token", null))
        setContent { MaterialTheme { SentinelScreen() } }
    }

    private fun batteryLevel(): Float? {
        val manager = getSystemService(BATTERY_SERVICE) as BatteryManager
        val level = manager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        return if (level in 0..100) level.toFloat() else null
    }

    private fun startTracking() {
        val fine = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (fine || coarse) tracker.start()
        else permissionLauncher.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
    }

    private fun triggerSOS(onStatus: (String) -> Unit, onFinished: (String) -> Unit) {
        scope.launch {
            for (seconds in 5 downTo 1) {
                onStatus("SOS will activate in ${seconds}s — tap Cancel to stop")
                delay(1000)
            }
            onStatus("Sending emergency alert...")
            runCatching {
                ApiClient.service.createSOS(
                    SOSCreate(
                        device_id = prefs.getString("device_id", null),
                        latitude = tracker.lastLatitude,
                        longitude = tracker.lastLongitude,
                        message = "Emergency SOS activated from Sentinel Android"
                    )
                )
            }.onSuccess { response ->
                prefs.edit().putString("active_sos_id", response.id).apply()
                onFinished("SOS ACTIVE — guardians can now respond")
            }.onFailure { onFinished("SOS failed: ${it.message ?: "unknown error"}") }
        }
    }

    private fun cancelSOS(onStatus: (String) -> Unit) {
        scope.coroutineContext.cancelChildren()
        onStatus("SOS cancelled")
    }

    @androidx.compose.runtime.Composable
    private fun SentinelScreen() {
        var email by remember { mutableStateOf("") }
        var password by remember { mutableStateOf("") }
        var deviceName by remember { mutableStateOf("My Sentinel Phone") }
        var status by remember { mutableStateOf(if (prefs.getString("device_id", null) != null) "Device paired" else "Not paired") }
        var sosActive by remember { mutableStateOf(prefs.getString("active_sos_id", null) != null) }
        var countdown by remember { mutableIntStateOf(0) }

        Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("Sentinel", style = MaterialTheme.typography.headlineLarge)
            Text("Personal Safety & Device Recovery")

            OutlinedTextField(email, { email = it }, Modifier.fillMaxWidth(), label = { Text("Email") })
            OutlinedTextField(password, { password = it }, Modifier.fillMaxWidth(), label = { Text("Password") })
            Button(onClick = {
                scope.launch {
                    status = "Signing in..."
                    runCatching {
                        val result = ApiClient.service.login(email.trim(), password)
                        prefs.edit().putString("token", result.access_token).apply()
                        ApiClient.setToken(result.access_token)
                    }.onSuccess { status = "Signed in" }.onFailure { status = "Login failed: ${it.message ?: "unknown error"}" }
                }
            }, Modifier.fillMaxWidth()) { Text("Sign in") }

            OutlinedTextField(deviceName, { deviceName = it }, Modifier.fillMaxWidth(), label = { Text("Device name") })
            Button(onClick = {
                scope.launch {
                    status = "Pairing device..."
                    val identifier = prefs.getString("device_identifier", null) ?: UUID.randomUUID().toString().also { prefs.edit().putString("device_identifier", it).apply() }
                    runCatching { ApiClient.service.registerDevice(DeviceCreate(deviceName.trim(), "android", identifier)) }
                        .onSuccess { prefs.edit().putString("device_id", it.id).apply(); status = "Device paired: ${it.name}" }
                        .onFailure { status = "Pairing failed: ${it.message ?: "unknown error"}" }
                }
            }, Modifier.fillMaxWidth()) { Text("Pair this phone") }

            Button(onClick = {
                if (prefs.getString("device_id", null) == null) status = "Pair the phone first"
                else { status = "Location tracking started"; startTracking() }
            }, Modifier.fillMaxWidth()) { Text("Start location tracking") }

            Text("Emergency Safety", style = MaterialTheme.typography.titleLarge)
            Text("Location is captured only from this explicitly paired device.")

            Button(
                enabled = !sosActive && countdown == 0 && prefs.getString("device_id", null) != null,
                onClick = {
                    countdown = 5
                    triggerSOS({ text -> status = text }, { text -> countdown = 0; status = text; sosActive = true })
                    scope.launch { for (i in 5 downTo 1) { countdown = i; delay(1000) } }
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text(if (countdown > 0) "SOS ACTIVATING… $countdown" else "🚨 EMERGENCY SOS") }

            if (countdown > 0) {
                OutlinedButton(onClick = { countdown = 0; cancelSOS { status = it } }, Modifier.fillMaxWidth()) { Text("Cancel SOS") }
            }
            if (sosActive) {
                OutlinedButton(onClick = { status = "Resolve the SOS from the dashboard" }, Modifier.fillMaxWidth()) { Text("SOS ACTIVE") }
            }

            Text("Status: $status")
            Text("Security: actions are restricted to your authenticated account and enrolled device.")
        }
    }

    override fun onDestroy() {
        if (::tracker.isInitialized) tracker.stop()
        super.onDestroy()
    }
}
