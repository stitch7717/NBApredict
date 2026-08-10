package com.nba.predict;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@MapperScan("com.nba.predict.mapper")
@EnableScheduling
public class NbaPredictApplication {

    public static void main(String[] args) {
        SpringApplication.run(NbaPredictApplication.class, args);
    }
}
