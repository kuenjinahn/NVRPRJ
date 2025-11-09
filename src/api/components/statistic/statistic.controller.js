import VideoReceiveData from '../../../models/VideoReceiveData.js';
import { Op, fn, col, literal } from 'sequelize';
import { getAllDetectionZones } from '../events/events.model.js';

export const getRealtimeTemp = async (req, res) => {
  try {
    const { cameraId } = req.query;
    const where = {};
    if (cameraId) where.fk_camera_id = cameraId;

    // 현재 시간에서 1분 전 시간 계산
    const oneMinuteAgo = new Date(Date.now() - 60 * 1000);
    where.create_date = {
      [Op.gte]: oneMinuteAgo
    };

    const rows = await VideoReceiveData.findAll({
      where,
      order: [['create_date', 'DESC']]
    });
    rows.reverse();
    const result = rows.map(row => {
      const v = row.getDataValue('data_value') || {};
      // JSON 파싱 추가
      const parsedV = typeof v === 'string' ? JSON.parse(v) : v;
      // console.log('======>  parsedV', parsedV);
      return {
        time: row.getDataValue('create_date'),
        rois: Array.from({ length: 10 }, (_, i) => parsedV[`data_${22 + i * 2}`] ?? null),
        min: parsedV.data_19 ?? null,
        max: parsedV.data_20 ?? null,
        avg: parsedV.data_21 ?? null
      };
    });
    res.json({ result });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

export const getDailyRoiMinChange = async (req, res) => {
  try {
    const { roiNumber, date } = req.query;
    const roiNum = parseInt(roiNumber);
    const targetDate = date ? new Date(date) : new Date();

    // 해당 날짜의 시작과 끝 시간 계산
    const startOfDay = new Date(targetDate);
    startOfDay.setHours(0, 0, 0, 0);
    const endOfDay = new Date(targetDate);
    endOfDay.setHours(23, 59, 59, 999);

    // ROI 번호에 해당하는 data 필드 인덱스 계산
    const baseIndex = 22 + (roiNum * 2);
    const minDataField = `data_${baseIndex}`;

    // 해당 날짜의 모든 데이터 조회
    const dailyData = await VideoReceiveData.findAll({
      where: {
        create_date: {
          [Op.between]: [startOfDay, endOfDay]
        }
      },
      order: [['create_date', 'ASC']],
      attributes: ['create_date', 'data_value']
    });

    // 최소 온도 변화 추적
    const minTemps = [];
    dailyData.forEach(data => {
      try {
        const dataValue = data.getDataValue('data_value') || {};
        const parsedDataValue = typeof dataValue === 'string' ? JSON.parse(dataValue) : dataValue;

        if (parsedDataValue[minDataField] !== undefined) {
          minTemps.push({
            time: data.getDataValue('create_date'),
            minTemp: Number(parsedDataValue[minDataField])
          });
        }
      } catch (error) {
        console.error('Error parsing data:', error);
      }
    });

    // 최소 온도 변화 계산
    const changes = [];
    for (let i = 1; i < minTemps.length; i++) {
      const change = minTemps[i].minTemp - minTemps[i - 1].minTemp;
      changes.push({
        time: minTemps[i].time,
        change: change.toFixed(1),
        previousMin: minTemps[i - 1].minTemp.toFixed(1),
        currentMin: minTemps[i].minTemp.toFixed(1)
      });
    }

    res.json({
      success: true,
      result: {
        roiNumber: roiNum,
        date: targetDate.toISOString().split('T')[0],
        dataCount: minTemps.length,
        changes: changes
      }
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};

export const getRoiDataList = async (req, res) => {
  try {
    // Get detection zones from events model
    const zones = await getAllDetectionZones();
    // console.log('======>  zones', zones);

    // Process each zone - 각 ROI에 대해 최신 데이터 조회
    const roiDataPromises = zones.map(async (zone) => {
      // zone_type에서 ROI 번호 추출 (Z0 -> 0, Z1 -> 1, Z2 -> 2, Z001 -> 1, ...)
      // zone_type의 숫자를 그대로 roiNumber로 사용
      let roiNumber = null;
      if (zone.zone_type) {
        const zoneTypeStr = zone.zone_type.toString();
        // "Z0", "Z00", "0" 등의 형식도 처리
        const match = zoneTypeStr.match(/Z?0*(\d+)/);
        if (match) {
          roiNumber = parseInt(match[1]); // Z0 -> 0, Z1 -> 1, Z2 -> 2, Z001 -> 1, ...
        }
      }

      // zone_type에서 추출 실패한 경우 zone_desc에서 시도 (예: "ROI-0" -> 0, "ROI-1" -> 1, "ROI-2" -> 2)
      if (roiNumber === null && zone.zone_desc) {
        const descMatch = zone.zone_desc.toString().match(/ROI[-\s]?(\d+)/i);
        if (descMatch) {
          roiNumber = parseInt(descMatch[1]);
        }
      }

      // ROI 번호가 없으면 기본값 반환 (roiNumber가 0일 수도 있으므로 null만 체크)
      if (roiNumber === null || isNaN(roiNumber)) {
        return {
          id: zone.id,
          zone_desc: zone.zone_desc,
          zone_type: zone.zone_type,
          maxTemp: '--',
          minTemp: '--',
          avgTemp: '--',
          alertLevel: zone.alert_level,
          temps: []
        };
      }

      // 해당 ROI 번호의 최신 데이터 조회 (roiNumber가 0일 수도 있으므로 명시적으로 처리)
      const latestData = await VideoReceiveData.findOne({
        where: {
          roiNumber: roiNumber
        },
        order: [['create_date', 'DESC']]
      });

      console.log(`[getRoiDataList] Zone: ${zone.zone_desc}, zone_type: ${zone.zone_type}, extracted roiNumber: ${roiNumber}, found data: ${latestData ? 'yes' : 'no'}`);

      let maxTemp = '--';
      let minTemp = '--';
      let avgTemp = '--';
      const temps = [];

      if (latestData) {
        // data_value JSON에서 온도 정보 추출
        const dataValue = latestData.getDataValue('data_value') || {};
        const parsedDataValue = typeof dataValue === 'string' ? JSON.parse(dataValue) : dataValue;

        // data_value JSON에 max_temp, min_temp, avg_temp가 있는 경우 사용
        if (parsedDataValue.max_temp !== undefined &&
          parsedDataValue.min_temp !== undefined &&
          parsedDataValue.avg_temp !== undefined) {
          maxTemp = parseFloat(parsedDataValue.max_temp).toFixed(1);
          minTemp = parseFloat(parsedDataValue.min_temp).toFixed(1);
          avgTemp = parseFloat(parsedDataValue.avg_temp).toFixed(1);

          temps.push({
            time: latestData.getDataValue('create_date'),
            min: minTemp,
            max: maxTemp,
            avg: avgTemp
          });
        }
      }

      return {
        id: zone.id,
        zone_desc: zone.zone_desc,
        zone_type: zone.zone_type,
        maxTemp,
        minTemp,
        avgTemp,
        alertLevel: zone.alert_level,
        temps: temps
      };
    });

    // 모든 Promise가 완료될 때까지 대기
    const roiData = await Promise.all(roiDataPromises);

    res.json({
      success: true,
      result: roiData
    });
  } catch (error) {
    console.error('Error in getRoiDataList:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get ROI data list'
    });
  }
};

// ROI 번호와 발생 일자를 받아서 해당 시간 이전의 1분 데이터를 조회하는 API
export const getRoiTimeSeriesData = async (req, res) => {
  try {
    const { roiNumber, eventDate } = req.query;

    if (!roiNumber || !eventDate) {
      return res.status(400).json({
        success: false,
        error: 'ROI 번호와 발생 일자는 필수입니다.'
      });
    }

    const roiNum = parseInt(roiNumber);
    if (isNaN(roiNum)) {
      return res.status(400).json({
        success: false,
        error: '유효하지 않은 ROI 번호입니다.'
      });
    }

    // eventDate를 Date 객체로 변환
    const eventDateTime = new Date(eventDate);
    if (isNaN(eventDateTime.getTime())) {
      return res.status(400).json({
        success: false,
        error: '유효하지 않은 날짜 형식입니다.'
      });
    }

    // 24시간 전 시간 계산
    const twentyFourHoursBefore = new Date(eventDateTime.getTime() - 24 * 60 * 60 * 1000);

    // VideoReceiveData에서 해당 ROI 번호의 eventDate 이전 24시간간 데이터 조회
    const timeSeriesData = await VideoReceiveData.findAll({
      where: {
        roiNumber: roiNum,
        create_date: {
          [Op.between]: [twentyFourHoursBefore, eventDateTime]
        }
      },
      order: [['create_date', 'ASC']],
      attributes: ['create_date', 'data_value', 'roiNumber']
    });

    console.log(`Found ${timeSeriesData.length} records for ROI ${roiNum} between ${twentyFourHoursBefore.toISOString()} and ${eventDateTime.toISOString()}`);

    // 온도 데이터 추출
    const temperatureData = [];
    const allMinTemps = [];
    const allMaxTemps = [];
    const allAvgTemps = [];

    timeSeriesData.forEach(data => {
      try {
        const dataValue = data.getDataValue('data_value') || {};
        const parsedDataValue = typeof dataValue === 'string' ? JSON.parse(dataValue) : dataValue;

        // data_value에서 max_temp, min_temp, avg_temp 추출
        // roiNumber 컬럼으로 이미 필터링되었으므로 추가 검증 불필요
        if (parsedDataValue.max_temp !== undefined &&
          parsedDataValue.min_temp !== undefined &&
          parsedDataValue.avg_temp !== undefined) {
          const minTemp = parseFloat(parsedDataValue.min_temp);
          const maxTemp = parseFloat(parsedDataValue.max_temp);
          const avgTemp = parseFloat(parsedDataValue.avg_temp);

          allMinTemps.push(minTemp);
          allMaxTemps.push(maxTemp);
          allAvgTemps.push(avgTemp);

          temperatureData.push({
            time: data.getDataValue('create_date'),
            min: minTemp.toFixed(1),
            max: maxTemp.toFixed(1),
            avg: avgTemp.toFixed(1),
            roiNumber: roiNum
          });
        }
      } catch (error) {
        console.error('Error parsing data for record:', data.id, error);
      }
    });

    // 통계 계산
    let maxTemp = '--';
    let minTemp = '--';
    let avgTemp = '--';

    if (allMinTemps.length > 0 && allMaxTemps.length > 0) {
      maxTemp = Math.max(...allMaxTemps).toFixed(1);
      minTemp = Math.min(...allMinTemps).toFixed(1);
      avgTemp = (allAvgTemps.reduce((a, b) => a + b, 0) / allAvgTemps.length).toFixed(1);
    }

    // 응답 데이터 구성
    const responseData = {
      roiNumber: parseInt(roiNumber),
      eventDate: eventDateTime.toISOString(),
      timeRange: {
        start: twentyFourHoursBefore.toISOString(),
        end: eventDateTime.toISOString()
      },
      statistics: {
        maxTemp,
        minTemp,
        avgTemp,
        dataCount: temperatureData.length
      },
      timeSeriesData: temperatureData
    };

    res.json({
      success: true,
      result: responseData
    });

  } catch (error) {
    console.error('Error in getRoiTimeSeriesData:', error);
    res.status(500).json({
      success: false,
      error: 'ROI 시계열 데이터 조회 중 오류가 발생했습니다.'
    });
  }
};

export const getRoiTemperatureTimeSeries = async (req, res) => {
  try {
    const { roiNumber } = req.query;

    // 필수 파라미터 검증
    if (!roiNumber) {
      return res.status(400).json({
        success: false,
        error: 'ROI 번호는 필수입니다.'
      });
    }

    const roiNum = parseInt(roiNumber);
    if (isNaN(roiNum)) {
      return res.status(400).json({
        success: false,
        error: '유효하지 않은 ROI 번호입니다.'
      });
    }

    // 24시간 전 시간 계산
    const now = new Date();
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    // VideoReceiveData에서 해당 ROI 번호의 최근 24시간 데이터 조회
    const allTimeSeriesData = await VideoReceiveData.findAll({
      where: {
        roiNumber: roiNum,
        create_date: {
          [Op.gte]: twentyFourHoursAgo
        }
      },
      order: [['create_date', 'ASC']], // 시간순 정렬 (오래된 것부터)
      attributes: ['create_date', 'data_value', 'roiNumber']
    });

    // 온도 데이터 추출 및 처리
    const temperatureData = [];

    allTimeSeriesData.forEach(data => {
      try {
        const dataValue = data.getDataValue('data_value') || {};
        const parsedDataValue = typeof dataValue === 'string' ? JSON.parse(dataValue) : dataValue;

        // data_value에서 max_temp, min_temp, avg_temp 추출
        // roiNumber 컬럼으로 이미 필터링되었으므로 추가 검증 불필요
        if (parsedDataValue.max_temp !== undefined &&
          parsedDataValue.min_temp !== undefined &&
          parsedDataValue.avg_temp !== undefined) {
          temperatureData.push({
            time: data.getDataValue('create_date'),
            min: parseFloat(parsedDataValue.min_temp).toFixed(1),
            max: parseFloat(parsedDataValue.max_temp).toFixed(1),
            avg: parseFloat(parsedDataValue.avg_temp).toFixed(1)
          });
        }
      } catch (error) {
        console.error('Error parsing data for record:', data.id, error);
      }
    });

    // 이미 시간순으로 정렬되어 있으므로 reverse 불필요
    console.log(`Found ${temperatureData.length} records for ROI ${roiNum} (last 24 hours)`);

    res.json({
      success: true,
      result: {
        roiNumber: roiNum,
        dataCount: temperatureData.length,
        timeRange: {
          start: twentyFourHoursAgo.toISOString(),
          end: now.toISOString()
        },
        timeSeriesData: temperatureData
      }
    });

  } catch (error) {
    console.error('Error in getRoiTemperatureTimeSeries:', error);
    res.status(500).json({
      success: false,
      error: 'ROI 온도 시계열 데이터 조회 중 오류가 발생했습니다.'
    });
  }
};
