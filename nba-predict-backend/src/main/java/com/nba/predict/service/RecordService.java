package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.PredictRecord;

import java.time.LocalDate;

public interface RecordService {

    Page<PredictRecord> listRecords(int page, int size, String predictType,
                                    LocalDate startDate, LocalDate endDate, String status);

    PredictRecord getRecordDetail(Long predictId);

    void calibrateRecord(Long predictId, Integer realPoints, Double realFgPct,
                         Integer realHomeScore, Integer realAwayScore);
}
