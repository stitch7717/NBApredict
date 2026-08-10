package com.nba.predict.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nba.predict.config.AlgorithmConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import okhttp3.*;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class HttpUtil {

    private final AlgorithmConfig algorithmConfig;
    private final ObjectMapper objectMapper;
    private final OkHttpClient httpClient;

    public HttpUtil(AlgorithmConfig algorithmConfig, ObjectMapper objectMapper) {
        this.algorithmConfig = algorithmConfig;
        this.objectMapper = objectMapper;
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(algorithmConfig.getConnectTimeout(), TimeUnit.MILLISECONDS)
                .readTimeout(algorithmConfig.getReadTimeout(), TimeUnit.MILLISECONDS)
                .writeTimeout(10, TimeUnit.SECONDS)
                .build();
    }

    /**
     * GET请求
     */
    public String get(String path) throws IOException {
        String url = algorithmConfig.getBaseUrl() + path;
        Request request = new Request.Builder()
                .url(url)
                .get()
                .build();
        return executeWithRetry(request);
    }

    /**
     * GET请求带参数
     */
    public String get(String path, Map<String, String> params) throws IOException {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(algorithmConfig.getBaseUrl() + path).newBuilder();
        if (params != null) {
            params.forEach(urlBuilder::addQueryParameter);
        }
        Request request = new Request.Builder()
                .url(urlBuilder.build())
                .get()
                .build();
        return executeWithRetry(request);
    }

    /**
     * POST请求
     */
    public String post(String path, Object body) throws IOException {
        String json = objectMapper.writeValueAsString(body);
        RequestBody requestBody = RequestBody.create(
                json, MediaType.parse("application/json; charset=utf-8"));
        Request request = new Request.Builder()
                .url(algorithmConfig.getBaseUrl() + path)
                .post(requestBody)
                .build();
        return executeWithRetry(request);
    }

    /**
     * 带重试的请求执行
     */
    private String executeWithRetry(Request request) throws IOException {
        int maxRetry = algorithmConfig.getRetryCount();
        IOException lastException = null;

        for (int i = 0; i <= maxRetry; i++) {
            try (Response response = httpClient.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    return response.body().string();
                }
                throw new IOException("请求失败: " + response.code());
            } catch (IOException e) {
                lastException = e;
                if (i < maxRetry) {
                    log.warn("算法调用失败，第{}次重试: {}", i + 1, e.getMessage());
                    try {
                        Thread.sleep(algorithmConfig.getRetryInterval());
                    } catch (InterruptedException ignored) {
                        Thread.currentThread().interrupt();
                    }
                }
            }
        }
        throw lastException;
    }
}
