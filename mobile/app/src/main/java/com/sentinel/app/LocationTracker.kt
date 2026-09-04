package com.sentinel.app

import android.annotation.SuppressLint
import android.content.Context
import android.os.Looper
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.Priority
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.time.Instant

class LocationTracker(
    context: Context,
    private val deviceIdProvider: () -> String?,
    private val batteryProvider: () -> Float?
) {
    private val client: FusedLocationProviderClient =
        com.google.android.gms.location.LocationServices.getFusedLocationProviderClient(context)
    private val scope = CoroutineScope(Dispatchers.IO)

    private val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 15_000L)
        .setMinUpdateIntervalMillis(10_000L)
        .setMinUpdateDistanceMeters(10f)
        .build()

    private val callback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val deviceId = deviceIdProvider() ?: return
            result.locations.forEach { location ->
                scope.launch {
                    runCatching {
                        ApiClient.service.updateLocation(
                            deviceId,
                            LocationPayload(
                                latitude = location.latitude,
                                longitude = location.longitude,
                                accuracy_m = location.accuracy,
                                battery_level = batteryProvider(),
                                recorded_at = Instant.ofEpochMilli(location.time).toString()
                            )
                        )
                    }
                }
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun start() {
        client.requestLocationUpdates(request, callback, Looper.getMainLooper())
    }

    fun stop() {
        client.removeLocationUpdates(callback)
    }
}
