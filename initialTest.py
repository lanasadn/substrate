from substrateinterface import SubstrateInterface
import pandas as pd
from time import sleep
from decimal import Decimal, getcontext,ROUND_HALF_UP
pd.options.display.max_rows = None
pd.options.display.max_columns = None
import os
from tqdm import tqdm

# block_number = 139696
# block_hash = substrate.get_block_hash(block_number)
# print(block_hash)

# result = substrate.query(
#     "System", "Account", ["5DyrSBNDRo6oaW4QPisptTYAoK6fsZovbQoxpE8L8ftCfd1n"], block_hash=block_hash
# )



def formatBalance(amount):
    if amount!=0:
        getcontext().prec = 30
        decimalOutput = Decimal(amount)/Decimal(10**18)
        return (decimalOutput)
    else: 
        return 0


# balance = (result.value["data"]["free"] + result.value["data"]["reserved"])

# print(f"Balance @ {block_number}: {format_balance(balance)}")

def getCurrentEra(substrate):
    result = substrate.query(
        "Staking", "CurrentEra"
    )
    return int(str(result))

# result = substrate.query(
#     "Staking", "CounterForValidators"
# )
# print(result)

# result = substrate.query(
#     "Staking", "ErasTotalStake",["31"]
# )
# print(result)

def validatorRewards(substrate,era):
    result = substrate.query(
        "Staking", "ErasValidatorReward",[str(era)]
    )
    return result

def validatorPref(substrate,era):
    result = substrate.query_map(
        "Staking", "ErasValidatorPrefs",[str(era)]
    )
    data = []
    for item in result:
        validator = str(item[0])
        if float(str(item[1]['commission']))<10:
            commission = 0.0
        else:
            commission = float(str(item[1]['commission']))/10**9
        blocked = (str(item[1]['blocked']))
        data.append([validator, commission,blocked])
    df = pd.DataFrame(data,columns = ["Validator", "CommissionRate","Blocked"])
    return df

def createInstance():
    substrate = SubstrateInterface(url="wss://turing-rpc.avail.so/ws")
    return substrate

def createDf(substrate,era):
    
    result = substrate.query(
        "Staking", "ErasRewardPoints",[str(era)]
    )
    df = pd.DataFrame(result['individual'],columns=["Validator","EraPoints"])
    df['Era'] = era
    df['EraPoints'] = df['EraPoints'].astype(str).astype(int)
    df['Validator'] = df['Validator'].astype(str)
    df = pd.DataFrame(df,columns=["Era","Validator","EraPoints"])
    return df


def getStake(substrate,era):
    result = substrate.query_map("Staking", "ErasStakersOverview", [str(era)])

    data = []
    for item in result:
        validator = str(item[0])
        total = formatBalance(str(item[1]['total']))
        own = formatBalance(str(item[1]['own']))
        nominator_count = item[1]['nominator_count']
        page_count = item[1]['page_count']
        
        # Calculate the Nominated value
        nominated = Decimal(total - own)
        
        data.append([validator, total, own, nominated, nominator_count, page_count])

    # Create a DataFrame with camel casing column names
    df = pd.DataFrame(data, columns=['Validator', 'TotalStake', 'OwnStake', 'NominatedStake', 'NomCount', 'PageCount'])

    return df

def loadData(substrate,era):
    df = createDf(substrate,era)
    df = pd.merge(df,getStake(substrate,era),how="inner")
    df = pd.merge(df,validatorPref(substrate,era),how="inner")
    
    totalRewards = formatBalance(str(validatorRewards(substrate,era)))
    
    totalEraPoints = df["EraPoints"].sum()
    for index, row in df.iterrows():
    
        df.at[index, 'CommissionEarned'] = Decimal(df.at[index,'EraPoints']/totalEraPoints)*Decimal(totalRewards)*Decimal(df.at[index, 'CommissionRate'])
        df.at[index, 'OwnReward'] =(Decimal(df.at[index,'EraPoints']/totalEraPoints)*Decimal(totalRewards)-df.at[index,"CommissionEarned"])*Decimal(df.at[index, 'OwnStake']/df.at[index, 'TotalStake'])
        df.at[index, "TotalReward"] = df.at[index, 'CommissionEarned']+df.at[index, 'OwnReward']
    # df['NomCount'] = df['NomCount'].astype(int)
    # df['PageCount'] = df['PageCount'].astype(int)
    df = df.sort_values(by='TotalStake', ascending=False)

    if not os.path.exists('ValidatorRewards.csv'):
        df.to_csv('ValidatorRewards.csv',index=False)
    else:
        df.to_csv('ValidatorRewards.csv',mode='a',index=False, header=False)
    

def getBlocks(substrate,era):
    # era = substrate.query(
    #         module='Staking',
    #         storage_function='CurrentEra'
    #     )
    blocks_per_era = substrate.query_map(
            module='Staking',
            storage_function='EraLength'
            
        )
    print(blocks_per_era[0])
    # for item in blocks_per_era:
    #     print(item)

def main():
    substrate = createInstance()
    era = getCurrentEra(substrate)

    if not os.path.exists('ValidatorRewards.csv'):
        startEra=0
    else:
        df = pd.read_csv('ValidatorRewards.csv')
        startEra = int(df.iloc[-1].iloc[0])+1

    
    for i in tqdm(range (startEra,era)):
        loadData(substrate,i)
        
main()


# substrate = createInstance()
# getBlocks(substrate,39)
# print(substrate.get_metadata_call_function("Balances","transfer_keep_alive","0x6a97388f03211c5903d99b98ad096d80864d2ff95a66e119dbc77d09440d03de"))
# address = "12D3KooWKaQEU4PRVmrcqEh6f7xW7PwP4YkbM7pTQDRND9ZL6Pnn"

# Convert to SS58 format
# ss58_address = substrate.ss58_decode(address)
# print(ss58_address)
# era = 39

# df = createDf(substrate,era)
# df = pd.merge(df,getStake(substrate,era),how="inner")
# df = pd.merge(df,validatorPref(substrate,era),how="inner")
# print(df)
# print(substrate.retrieve_extrinsic_by_hash("0x280400000000000000"))
# print(validatorPref(substrate, 32,"5D5dTdfs3d3fpn4DSUC6fE269b4kgVbdcrVsXuJ2XSmm96i6"))
# print(formatBalance(str(validatorRewards(substrate))))
# print(getCurrentEra(substrate))

# value = getStake("5D5dTdfs3d3fpn4DSUC6fE269b4kgVbdcrVsXuJ2XSmm96i6",substrate,39)
# print(value)
# print(formatBalance(value))
# print(substrate.properties.get('tokenDecimals', 0))