"""测试 DeepSeek-R1-Distill-Qwen-14B 推理部署"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_PATH = "/home/ll_yqs2/models/Qwen3.5-9B"
DEVICE_NO = 2
def main():
    print(f"正在加载模型: {MODEL_PATH}")
    print(f"GPU: {torch.cuda.get_device_name(DEVICE_NO)}")
    print(f"显存: {torch.cuda.get_device_properties(DEVICE_NO).total_memory / 1024**3:.1f} GB")

    # 加载 tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)

    # 加载模型（FP16，自动分配到 GPU 1 即 A6000）
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map=DEVICE_NO,
        trust_remote_code=True,
    )
    print("模型加载完成！")

    # 测试对话
    questions = [
        '''
        如何解决以下报错：
        "(chuma-llm) ll_yqs2@a-Super-Server:~$ python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
/home/ll_yqs2/data/anaconda3/envs/chuma-llm/lib/python3.11/site-packages/torch/cuda/__init__.py:180: UserWarning: CUDA initialization: The NVIDIA driver on your system is too old (found version 12050). Please update your GPU driver by downloading and installing a new version from the URL: http://www.nvidia.com/Download/index.aspx Alternatively, go to: https://pytorch.org to install a PyTorch version that has been compiled with your version of the CUDA driver. (Triggered internally at /pytorch/c10/cuda/CUDAFunctions.cpp:119.)
  return torch._C._cuda_getDeviceCount() > 0
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/home/ll_yqs2/data/anaconda3/envs/chuma-llm/lib/python3.11/site-packages/torch/cuda/__init__.py", line 653, in get_device_name
    return get_device_properties(device).name
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ll_yqs2/data/anaconda3/envs/chuma-llm/lib/python3.11/site-packages/torch/cuda/__init__.py", line 686, in get_device_properties
    _lazy_init()  # will define _get_device_properties
    ^^^^^^^^^^^^
  File "/home/ll_yqs2/data/anaconda3/envs/chuma-llm/lib/python3.11/site-packages/torch/cuda/__init__.py", line 478, in _lazy_init
    torch._C._cuda_init()
RuntimeError: The NVIDIA driver on your system is too old (found version 12050). Please update your GPU driver by downloading and installing a new version from the URL: http://www.nvidia.com/Download/index.aspx Alternatively, go to: https://pytorch.org to install a PyTorch version that has been compiled with your version of the CUDA driver.
    "
    '''
    ]

    for q in questions:
        print(f"\n{'='*60}")
        print(f"问题: {q}")
        print(f"{'='*60}")

        messages = [{"role": "user", "content": "<think>\n\n</think>" + q}]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
            )

        response = tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
        )
        print(f"\n回答:\n{response}")

        # 显存使用情况
        mem_used = torch.cuda.memory_allocated(DEVICE_NO) / 1024**3
        mem_total = torch.cuda.get_device_properties(DEVICE_NO).total_memory / 1024**3
        print(f"\n显存使用: {mem_used:.1f} / {mem_total:.1f} GB")


if __name__ == "__main__":
    main()
