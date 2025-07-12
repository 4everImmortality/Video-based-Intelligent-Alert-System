import os
import logging
from ultralytics import YOLO
from config import BEHAVIOR_MODEL_MAP, BEHAVIOR_CLASSES_MAP, DEFAULT_MODEL_PATH

logger = logging.getLogger(__name__)

def validate_model_files():
    """
    验证所有配置的模型文件是否存在
    """
    missing_models = []
    
    # 检查默认模型
    if not os.path.exists(DEFAULT_MODEL_PATH):
        missing_models.append(f"Default model: {DEFAULT_MODEL_PATH}")
    
    # 检查behavior特定模型
    for behavior, model_path in BEHAVIOR_MODEL_MAP.items():
        if not os.path.exists(model_path):
            missing_models.append(f"Behavior {behavior}: {model_path}")
    
    if missing_models:
        logger.warning("Missing model files:")
        for missing in missing_models:
            logger.warning(f"  - {missing}")
        return False
    
    logger.info("All model files validated successfully.")
    return True

def test_open_vocabulary_models():
    """
    测试开放词汇模型的类别设置功能
    """
    logger.info("Testing open vocabulary models...")
    
    for behavior, classes in BEHAVIOR_CLASSES_MAP.items():
        model_path = BEHAVIOR_MODEL_MAP.get(behavior)
        if not model_path or not os.path.exists(model_path):
            logger.warning(f"Model not found for behavior {behavior}: {model_path}")
            continue
            
        try:
            logger.info(f"Testing model {model_path} with classes {classes}")
            model = YOLO(model_path)
            
            # 测试设置类别
            model.set_classes(classes)
            logger.info(f"✓ Successfully set classes for {behavior}: {classes}")
            
            # 如果可能，显示模型的当前类别信息
            if hasattr(model, 'names'):
                logger.info(f"  Model names: {model.names}")
            
        except Exception as e:
            logger.error(f"✗ Failed to test model {model_path}: {e}")

def preload_all_models():
    """
    预加载所有模型以检测配置问题，包括类别设置
    """
    models = {}
    
    try:
        # 加载默认模型
        logger.info(f"Loading default model: {DEFAULT_MODEL_PATH}")
        models['default'] = YOLO(DEFAULT_MODEL_PATH)
        
        # 加载behavior特定模型
        for behavior, model_path in BEHAVIOR_MODEL_MAP.items():
            if model_path != DEFAULT_MODEL_PATH:  # 避免重复加载
                logger.info(f"Loading model for {behavior}: {model_path}")
                model = YOLO(model_path)
                
                # 如果该behavior有特定类别配置，测试设置
                if behavior in BEHAVIOR_CLASSES_MAP:
                    classes = BEHAVIOR_CLASSES_MAP[behavior]
                    logger.info(f"Setting classes for {behavior}: {classes}")
                    try:
                        model.set_classes(classes)
                        logger.info(f"✓ Classes set successfully")
                    except Exception as e:
                        logger.warning(f"⚠ Failed to set classes: {e}")
                
                models[behavior] = model
        
        logger.info(f"Successfully loaded {len(models)} models.")
        return models
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        return None

if __name__ == "__main__":
    # 验证和测试模型加载
    print("Validating model files...")
    validate_model_files()
    
    print("Testing open vocabulary model features...")
    test_open_vocabulary_models()
    
    print("Testing all model loading...")
    models = preload_all_models()
    if models:
        print("All models loaded successfully!")
        for name, model in models.items():
            print(f"  - {name}: {type(model)}")
            if hasattr(model, 'names'):
                print(f"    Classes: {list(model.names.values()) if isinstance(model.names, dict) else model.names}")
    else:
        print("Model loading failed!")