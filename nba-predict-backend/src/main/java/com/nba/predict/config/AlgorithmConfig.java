package com.nba.predict.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "algorithm")
public class AlgorithmConfig {

    private String baseUrl = "http://localhost:8000";
    private int connectTimeout = 5000;
    private int readTimeout = 10000;
    private int retryCount = 2;
    private int retryInterval = 1000;
}
