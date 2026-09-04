package com.sentinel.app

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.POST
import retrofit2.http.Path

private const val API_BASE_URL = "http://10.0.2.2:8000/"

data class TokenResponse(val access_token: String, val token_type: String)
data class DeviceCreate(val name: String, val platform: String, val device_identifier: String)
data class DeviceResponse(
    val id: String,
    val name: String,
    val platform: String,
    val device_identifier: String
)
data class LocationPayload(
    val latitude: Double,
    val longitude: Double,
    val accuracy_m: Float?,
    val battery_level: Float?,
    val recorded_at: String?
)

interface SentinelApi {
    @FormUrlEncoded
    @POST("api/v1/auth/login")
    suspend fun login(
        @Field("username") email: String,
        @Field("password") password: String
    ): TokenResponse

    @POST("api/v1/devices")
    suspend fun registerDevice(
        @Body device: DeviceCreate
    ): DeviceResponse

    @POST("api/v1/devices/{deviceId}/location")
    suspend fun updateLocation(
        @Path("deviceId") deviceId: String,
        @Body location: LocationPayload
    ): Response<Unit>
}

object ApiClient {
    val service: SentinelApi by lazy {
        retrofit2.Retrofit.Builder()
            .baseUrl(API_BASE_URL)
            .addConverterFactory(retrofit2.converter.gson.GsonConverterFactory.create())
            .build()
            .create(SentinelApi::class.java)
    }
}
