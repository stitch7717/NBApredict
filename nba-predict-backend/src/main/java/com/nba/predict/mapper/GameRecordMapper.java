package com.nba.predict.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nba.predict.entity.GameRecord;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface GameRecordMapper extends BaseMapper<GameRecord> {
}
