package com.sentinel.app

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

data class TokenResponse(val access_token: String, val token_type: String)
data class DeviceCreate(val name: String, val platform: String, val device_identifier: String)
data class DeviceResponse(val id: String, val name: String, val platform: String, val device_identifier: String)
data class LocationPayload(val latitude: Double, val longitude: Double, val accuracy_m: Float?, val battery_level: Float?, val recorded_at: String?)
data class LocationResponse(val latitude: Double, val longitude: Double, val accuracy_m: Float?, val battery_level: Float?, val recorded_at: String?, val id: String, val device_id: String, val received_at: String)
data class SOSCreate(val device_id: String?, val latitude: Double?, val longitude: Double?, val message: String?)
data class SOSResponse(val id: String, val device_id: String?, val status: String, val latitude: Double?, val longitude: Double?, val message: String?, val created_at: String, val acknowledged_at: String?, val resolved_at: String?)
data class GuardianCreate(val name: String, val phone: String, val email: String?)
data class GuardianResponse(val id: String, val name: String, val phone: String, val email: String?, val created_at: String)
data class JourneyCreate(val device_id: String?, val destination: String, val start_latitude: Double?, val start_longitude: Double?, val end_latitude: Double?, val end_longitude: Double?, val eta: String)
data class JourneyResponse(val id: String, val device_id: String?, val destination: String, val start_latitude: Double?, val start_longitude: Double?, val end_latitude: Double?, val end_longitude: Double?, val eta: String, val status: String, val risk_score: Int, val created_at: String, val completed_at: String?)
data class JourneyPointPayload(val latitude: Double, val longitude: Double, val speed_mps: Float?, val bearing: Float?, val battery_level: Float?, val recorded_at: String?)
data class JourneyPointResponse(val id: String, val journey_id: String, val latitude: Double, val longitude: Double, val speed_mps: Float?, val bearing: Float?, val battery_level: Float?, val recorded_at: String?)

interface SentinelApi {
    @FormUrlEncoded @POST("api/v1/auth/login")
    suspend fun login(@Field("username") email: String, @Field("password") password: String): TokenResponse
    @POST("api/v1/devices") suspend fun registerDevice(@Body device: DeviceCreate): DeviceResponse
    @POST("api/v1/devices/{deviceId}/location") suspend fun updateLocation(@Path("deviceId") deviceId: String, @Body location: LocationPayload): LocationResponse
    @POST("api/v1/safety/sos") suspend fun createSOS(@Body sos: SOSCreate): SOSResponse
    @POST("api/v1/safety/guardians") suspend fun addGuardian(@Body guardian: GuardianCreate): GuardianResponse
    @GET("api/v1/safety/guardians") suspend fun listGuardians(): List<GuardianResponse>
    @POST("api/v1/journeys") suspend fun createJourney(@Body journey: JourneyCreate): JourneyResponse
    @GET("api/v1/journeys/{journeyId}") suspend fun getJourney(@Path("journeyId") journeyId: String): JourneyResponse
    @POST("api/v1/journeys/{journeyId}/points") suspend fun addJourneyPoint(@Path("journeyId") journeyId: String, @Body point: JourneyPointPayload): JourneyPointResponse
    @POST("api/v1/journeys/{journeyId}/complete") suspend fun completeJourney(@Path("journeyId") journeyId: String): JourneyResponse
}

class AuthInterceptor(private val tokenProvider: () -> String?) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): okhttp3.Response {
        val request = chain.request().newBuilder().apply { tokenProvider()?.takeIf { it.isNotBlank() }?.let { addHeader("Authorization", "Bearer $it") } }.build()
        return chain.proceed(request)
    }
}

object ApiClient {
    @Volatile private var token: String? = null
    fun setToken(value: String?) { token = value }
    val service: SentinelApi by lazy {
        val client = OkHttpClient.Builder().addInterceptor(AuthInterceptor { token }).build()
        Retrofit.Builder().baseUrl("http://10.0.2.2:8000/").client(client).addConverterFactory(GsonConverterFactory.create()).build().create(SentinelApi::class.java)
    }
}
