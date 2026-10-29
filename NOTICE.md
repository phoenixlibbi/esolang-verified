# Third-party material

## EsoLang-Bench dataset (CC BY 4.0)
`esoforge/data/esolang_bench.jsonl` is an unmodified copy of `data/test.jsonl` from
[Lossfunk/Esolang-Bench](https://huggingface.co/datasets/Lossfunk/Esolang-Bench) at revision
`a38a25fc6a19f477935f3b3f75567f88cefe8694` (Sharma & Chopra, 2026, arXiv:2603.09678),
licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The SHA-256 is pinned
in `esoforge/dataset.py` and checked on load.

## Official interpreters and harness (MIT)
`esoforge/upstream/*.py` are unmodified copies of `benchmark_harness/interpreters/*.py` and
`benchmark_harness/harness.py` from
[Lossfunk/esolang-metaprogramming](https://github.com/Lossfunk/esolang-metaprogramming) at commit
`b93ef26f1ff0c08a957c0ecc8397f21eb9ec247d` (Sharma, Thorat & Chopra, 2026, arXiv:2606.10933),
MIT licence, copied in `esoforge/upstream/LICENSE`. Their hashes are pinned in
`tests/test_upstream_pinned.py`.

Everything else in this repository is original work under the MIT licence in `LICENSE`.
