from typing import List, Optional
from pydantic import BaseModel


class SkuDef(BaseModel):
    price: Optional[float] = None
    promotionPrice: Optional[float] = None


class ItemSku(BaseModel):
    def_: Optional[SkuDef] = None

    class Config:
        fields = {
            'def_': 'def'
        }


class ItemData(BaseModel):
    itemId: str
    title: str
    itemUrl: str
    image: str
    sku: Optional[ItemSku] = None


class ResultListItem(BaseModel):
    item: ItemData
    delivery: Optional[dict] = None
    sellingPoints: Optional[dict] = None


class Status(BaseModel):
    code: int
    data: str


class Result(BaseModel):
    status: Status
    resultList: List[ResultListItem]


class AliexpressSearchResponse(BaseModel):
    result: Result

    def get_products(self) -> List[dict]:
        products = []
        for result_item in self.result.resultList:
            price = None
            if result_item.item.sku and result_item.item.sku.def_:
                price = (result_item.item.sku.def_.price or
                         result_item.item.sku.def_.promotionPrice)

            item_url = result_item.item.itemUrl
            if item_url.startswith('//'):
                item_url = f"https:{item_url}"

            image_url = result_item.item.image
            if image_url.startswith('//'):
                image_url = f"https:{image_url}"

            products.append({
                'source': 'aliexpress',
                'external_id': result_item.item.itemId,
                'name': result_item.item.title,
                'url_website': item_url,
                'url_image': image_url,
                'price': price
            })

        return products
