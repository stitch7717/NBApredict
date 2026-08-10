package com.nba.predict.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nba.predict.entity.PredictRecord;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface PredictRecordMapper extends BaseMapper<PredictRecord> {
}
