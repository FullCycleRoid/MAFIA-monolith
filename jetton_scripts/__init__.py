import asyncio

from jetton_scripts.deploy_testnet_jetton import main

if __name__ == "__main__":
    # For deployment script
    asyncio.run(main())

    # For local init
    # asyncio.run(init_local_data())

    # For testnet TON
    # asyncio.run(get_testnet_tons())
